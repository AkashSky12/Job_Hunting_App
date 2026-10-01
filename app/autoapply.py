"""Assisted auto-apply for ATS-hosted application forms (Greenhouse, Lever, Ashby, generic).

Opens the job URL in a visible Chromium window, locates standard fields by stable
ATS selectors first and accessible labels second, fills the applicant profile,
attaches the resume PDF, and by default stops so the user can review and submit.
CAPTCHAs / bot challenges are never bypassed: they are reported as ``needs_human``.

Setup:  pip install playwright && playwright install chromium
Usage:  python -m app.autoapply <job_url> [--resume cv.pdf] [--submit] [--job-id ID]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .config import BASE_DIR, settings
from .db import get_conn, row_to_dict

try:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright
except ImportError:  # optional dependency
    async_playwright = None
    PlaywrightError = Exception

log = logging.getLogger(__name__)

ARTIFACTS_DIR = BASE_DIR / "artifacts"
MAX_RESUME_BYTES = 10 * 1024 * 1024

_CHALLENGE_RE = re.compile(r"recaptcha|hcaptcha|challenges\.cloudflare\.com|turnstile|arkoselabs|funcaptcha", re.I)
_APPLY_RE = re.compile(r"^\s*(apply( now| for this (job|position|role))?|i'?m interested)\s*$", re.I)
_SUBMIT_RE = re.compile(r"submit( application)?|send application", re.I)
_CONFIRM_RE = re.compile(r"thank you|application (has been |was )?(received|submitted)", re.I)
_RESUME_RE = re.compile(r"resume|\bcv\b|curriculum", re.I)

_TEXTLIKE_JS = """e => !e.disabled && !e.readOnly && (e.tagName === 'TEXTAREA' ||
  (e.tagName === 'INPUT' && ['text', 'email', 'tel', 'url', 'search'].includes(e.type)))"""
_UNFILLED_REQUIRED_JS = """els => els.filter(e => e.offsetParent !== null && (!e.checkValidity() ||
  (e.getAttribute('aria-required') === 'true' && !String(e.value || '').trim()))).length"""


@dataclass
class ApplicantProfile:
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def from_db(cls) -> "ApplicantProfile":
        with get_conn() as conn:
            row = row_to_dict(conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()) or {}
        parsed = row.get("parsed_json") if isinstance(row.get("parsed_json"), dict) else {}
        first, _, last = (row.get("full_name") or parsed.get("name") or "").strip().partition(" ")
        return cls(
            first_name=first,
            last_name=last.strip(),
            email=row.get("email") or parsed.get("email") or "",
            phone=parsed.get("phone") or "",
            location=settings.applicant_location,
            linkedin=settings.applicant_linkedin,
            github=settings.applicant_github,
            portfolio=settings.applicant_portfolio,
        )


@dataclass(frozen=True)
class FieldSpec:
    key: str                     # attribute on ApplicantProfile
    label: str                   # accessible-label regex (fallback)
    selectors: tuple[str, ...]   # known stable ATS selectors (tried first)


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("first_name", r"first\s*name|given\s*name",
              ("#first_name", "input[name='first_name']", "input[autocomplete='given-name']")),
    FieldSpec("last_name", r"last\s*name|surname|family\s*name",
              ("#last_name", "input[name='last_name']", "input[autocomplete='family-name']")),
    FieldSpec("full_name", r"^\W*(full\s*)?name\W*$",
              ("input[name='name']", "#_systemfield_name", "input[autocomplete='name']")),
    FieldSpec("email", r"e-?mail",
              ("#email", "input[name='email']", "#_systemfield_email", "input[type='email']")),
    FieldSpec("phone", r"phone|mobile",
              ("#phone", "input[name='phone']", "input[type='tel']")),
    FieldSpec("location", r"^\W*(current\s*)?(location|city)\b",
              ("input[name='location']", "#candidate-location")),
    FieldSpec("linkedin", r"linked\s*in",
              ("input[name='urls[LinkedIn]']",)),
    FieldSpec("github", r"git\s*hub",
              ("input[name='urls[GitHub]']",)),
    FieldSpec("portfolio", r"portfolio|personal\s*(web)?site|^\W*website",
              ("input[name='urls[Portfolio]']", "input[name='urls[Other]']")),
)


@dataclass
class ApplyResult:
    url: str
    status: str = "pending"      # filled | submitted | needs_human | failed
    filled: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    resume_attached: bool = False
    unfilled_required: int = 0
    screenshot: str | None = None
    error: str | None = None


def _validate_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError(f"Not an http(s) URL: {url!r}")
    return url


def _validate_resume(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Resume not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError("Resume must be a PDF.")
    if p.stat().st_size > MAX_RESUME_BYTES:
        raise ValueError("Resume exceeds 10 MB.")
    return p


class AutoApplyEngine:
    def __init__(self, profile: ApplicantProfile, resume_path: str | Path, *,
                 headless: bool = False, timeout_ms: int = 15_000):
        if async_playwright is None:
            raise RuntimeError("Playwright not installed: pip install playwright && playwright install chromium")
        self.profile = profile
        self.resume = _validate_resume(resume_path)
        self.headless = headless
        self.timeout_ms = timeout_ms

    async def apply(self, url: str, *, submit: bool = False, keep_open: bool = True) -> ApplyResult:
        result = ApplyResult(_validate_url(url))
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            page.set_default_timeout(self.timeout_ms)
            try:
                await self._run(page, result, submit)
            except PlaywrightError as exc:
                log.exception("Auto-apply failed for %s", url)
                result.status, result.error = "failed", f"{type(exc).__name__}: {exc}"
            finally:
                result.screenshot = await self._screenshot(page)
                if keep_open and not self.headless and result.status != "submitted":
                    log.info("Review the form in the browser; close the tab when done.")
                    try:
                        await page.wait_for_event("close", timeout=0)
                    except PlaywrightError:
                        pass
                await browser.close()
        return result

    # ------------------------------------------------------------- workflow --
    async def _run(self, page, result: ApplyResult, submit: bool) -> None:
        await page.goto(result.url, wait_until="domcontentloaded")
        await self._settle(page)
        if await self._find(page, _spec("email")) is None:
            await self._open_application(page)

        # Lever/Ashby parse the resume and prefill fields asynchronously, so attach first.
        result.resume_attached = await self._attach_resume(page)
        if result.resume_attached:
            await page.wait_for_timeout(1500)

        await self._fill_fields(page, result)
        result.unfilled_required = await self._unfilled_required(page)

        if self._challenge_present(page):
            result.status = "needs_human"
            result.error = "CAPTCHA / bot challenge present; complete it in the browser."
        elif not submit:
            result.status = "filled"
        elif result.unfilled_required or not result.resume_attached:
            result.status = "needs_human"
            result.error = (f"Not submitting: {result.unfilled_required} required field(s) empty, "
                            f"resume attached={result.resume_attached}.")
        else:
            await self._submit(page, result)

    async def _settle(self, page) -> None:
        try:
            await page.locator("form, input, textarea").first.wait_for(state="attached", timeout=self.timeout_ms)
        except PlaywrightError:
            pass  # job-description pages may have no form yet

    async def _open_application(self, page) -> None:
        for role in ("link", "button"):
            btn = page.get_by_role(role, name=_APPLY_RE).first
            if not await btn.count() or not await btn.is_visible():
                continue
            href = await btn.get_attribute("href") if role == "link" else None
            target = urljoin(page.url, href) if href else None
            # Navigate in-page rather than clicking so target=_blank links don't spawn tabs.
            if target and urlparse(target).scheme in ("http", "https"):
                await page.goto(target, wait_until="domcontentloaded")
            else:
                await btn.click()
            await self._settle(page)
            return

    def _frames(self, page):
        return [f for f in page.frames if not _CHALLENGE_RE.search(f.url or "")]

    def _challenge_present(self, page) -> bool:
        return any(_CHALLENGE_RE.search(f.url or "") for f in page.frames)

    async def _find(self, page, spec: FieldSpec):
        for frame in self._frames(page):
            candidates = [frame.locator(s) for s in spec.selectors]
            candidates.append(frame.get_by_label(re.compile(spec.label, re.I)))
            for loc in candidates:
                try:
                    count = min(await loc.count(), 5)
                except PlaywrightError:
                    break  # frame detached
                for i in range(count):
                    el = loc.nth(i)
                    try:
                        if await el.is_visible() and await el.evaluate(_TEXTLIKE_JS):
                            return el
                    except PlaywrightError:
                        continue
        return None

    async def _fill_fields(self, page, result: ApplyResult) -> None:
        for spec in FIELDS:
            if spec.key == "full_name" and "first_name" in result.filled:
                continue
            value = getattr(self.profile, spec.key)
            if not value:
                continue
            el = await self._find(page, spec)
            if el is None:
                result.missing.append(spec.key)
                continue
            try:
                await el.fill(value)
                result.filled.append(spec.key)
            except PlaywrightError as exc:
                log.warning("Could not fill %s: %s", spec.key, exc)
                result.missing.append(spec.key)
        if "full_name" in result.filled or "first_name" in result.filled:
            result.missing = [k for k in result.missing if k not in ("first_name", "last_name", "full_name")]

    async def _attach_resume(self, page) -> bool:
        for frame in self._frames(page):
            try:
                inputs = frame.locator("input[type=file]")
                count = await inputs.count()
                if not count:
                    continue
                target = inputs.first
                for i in range(count):
                    hint = await inputs.nth(i).evaluate(
                        "e => [e.id, e.name, e.getAttribute('aria-label'),"
                        " (e.closest('label, fieldset') || e.parentElement)?.innerText?.slice(0, 200)].join(' ')"
                    )
                    if _RESUME_RE.search(hint or ""):
                        target = inputs.nth(i)
                        break
                await target.set_input_files(str(self.resume))
                return True
            except PlaywrightError as exc:
                log.warning("Resume upload via input failed: %s", exc)

        # Fallback: upload widgets that only create a file input on click.
        btn = page.get_by_role("button", name=re.compile(r"(attach|upload).*(resume|cv)|^\s*(attach|upload)\s*$", re.I)).first
        try:
            if await btn.count():
                async with page.expect_file_chooser(timeout=5000) as chooser_info:
                    await btn.click()
                await (await chooser_info.value).set_files(str(self.resume))
                return True
        except PlaywrightError as exc:
            log.warning("Resume upload via file chooser failed: %s", exc)
        return False

    async def _unfilled_required(self, page) -> int:
        total = 0
        for frame in self._frames(page):
            try:
                total += await frame.locator("input:not([type=hidden]), textarea, select").evaluate_all(
                    _UNFILLED_REQUIRED_JS
                )
            except PlaywrightError:
                continue
        return total

    async def _submit(self, page, result: ApplyResult) -> None:
        for frame in self._frames(page):
            btn = frame.get_by_role("button", name=_SUBMIT_RE).first
            if await btn.count() and await btn.is_visible():
                await btn.click()
                break
        else:
            result.status, result.error = "needs_human", "Submit button not found."
            return
        try:
            await page.get_by_text(_CONFIRM_RE).first.wait_for(timeout=self.timeout_ms)
            result.status = "submitted"
        except PlaywrightError:
            result.status = "needs_human"
            result.error = "Clicked submit but no confirmation detected; check the browser."

    async def _screenshot(self, page) -> str | None:
        try:
            ARTIFACTS_DIR.mkdir(exist_ok=True)
            path = ARTIFACTS_DIR / f"apply-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.png"
            await page.screenshot(path=str(path), full_page=True)
            return str(path)
        except PlaywrightError:
            return None


def _spec(key: str) -> FieldSpec:
    return next(s for s in FIELDS if s.key == key)


def record_application(job_id: str, result: ApplyResult) -> None:
    """Append an auto-apply event to the application timeline; mark applied on submit."""
    status = "applied" if result.status == "submitted" else "queued"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone():
            log.warning("Job %s not in database; skipping tracking.", job_id)
            return
        row = conn.execute("SELECT events FROM applications WHERE job_id = ?", (job_id,)).fetchone()
        events = json.loads(row["events"] or "[]") if row else []
        events.append({"type": f"auto_apply_{result.status}", "at": now})
        conn.execute(
            """
            INSERT INTO applications (job_id, status, events, applied_at, updated_at)
            VALUES (?, ?, ?, CASE WHEN ? = 'applied' THEN datetime('now') END, datetime('now'))
            ON CONFLICT(job_id) DO UPDATE SET
                events = excluded.events,
                status = CASE WHEN excluded.status = 'applied' THEN 'applied' ELSE applications.status END,
                applied_at = COALESCE(applications.applied_at, excluded.applied_at),
                updated_at = datetime('now')
            """,
            (job_id, status, json.dumps(events), status),
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-fill a job application form and attach your resume.")
    ap.add_argument("url", help="Job posting or application URL")
    ap.add_argument("--resume", default=settings.resume_path, help="Path to resume PDF (default: RESUME_PATH)")
    ap.add_argument("--submit", action="store_true", help="Submit if all required fields are filled and no CAPTCHA")
    ap.add_argument("--job-id", help="Job id from the local DB to record on the application timeline")
    ap.add_argument("--headless", action="store_true", help="Run without a visible browser")
    args = ap.parse_args(argv)
    if not args.resume:
        ap.error("--resume or RESUME_PATH is required")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = AutoApplyEngine(ApplicantProfile.from_db(), args.resume, headless=args.headless)
    result = asyncio.run(engine.apply(args.url, submit=args.submit, keep_open=not args.headless))
    if args.job_id:
        record_application(args.job_id, result)
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.status in ("filled", "submitted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
