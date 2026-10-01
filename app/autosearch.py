"""Keyword-driven auto-search over public ATS job-board APIs.

Greenhouse, Lever and Ashby publish official, unauthenticated JSON feeds for every
company board they host. Using them instead of scraping rendered HTML means no
brittle DOM selectors, no ToS conflicts, and structured fields out of the box.

Configure boards via ATS_BOARDS, e.g. "greenhouse:stripe,lever:palantir,ashby:ramp".
"""
from __future__ import annotations

import asyncio
import html
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

import httpx

from .config import settings
from .jobs import _clean, upsert_jobs

log = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "AI-Job-Hunter/1.0 (personal job search)"}
_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Board:
    ats: str
    token: str

    @classmethod
    def parse(cls, spec: str) -> "Board":
        ats, sep, token = spec.strip().partition(":")
        ats = ats.lower()
        # Slug is interpolated into the API URL path, so it must be strictly validated.
        if not sep or ats not in _ADAPTERS or not _SLUG_RE.fullmatch(token):
            raise ValueError(f"Invalid board {spec!r}; expected '<greenhouse|lever|ashby>:<slug>'")
        return cls(ats, token)

    @property
    def key(self) -> str:
        return f"{self.ats}:{self.token}"

    @property
    def url(self) -> str:
        return _ADAPTERS[self.ats][0].format(token=self.token)

    def parse_payload(self, payload) -> list[dict]:
        return _ADAPTERS[self.ats][1](self, payload)


def _job(board: Board, *, ext_id, title, company, location, remote, description,
         apply_url, posted_at, tags: Iterable[str | None]) -> dict:
    return {
        "id": f"{board.ats}:{board.token}:{ext_id}",
        "source": board.ats,
        "external_id": str(ext_id),
        "title": _clean(title),
        "company": _clean(company) or board.token,
        "location": _clean(location) or "Unknown",
        "remote": int(bool(remote)),
        "salary_min": None,
        "salary_max": None,
        "description": _clean(description)[:6000],
        "tags": [t for t in tags if t],
        "apply_url": apply_url or "",
        "posted_at": posted_at or "",
    }


def _greenhouse(board: Board, payload: dict) -> list[dict]:
    out = []
    for it in payload.get("jobs", []):
        loc = (it.get("location") or {}).get("name", "")
        out.append(_job(
            board,
            ext_id=it["id"],
            title=it.get("title"),
            company=it.get("company_name") or board.token,
            location=loc,
            remote="remote" in loc.lower(),
            # Greenhouse returns entity-escaped HTML; unescape before stripping tags.
            description=html.unescape(it.get("content") or ""),
            apply_url=it.get("absolute_url"),
            posted_at=it.get("updated_at"),
            tags=[d.get("name") for d in it.get("departments") or []],
        ))
    return out


def _lever(board: Board, payload: list) -> list[dict]:
    out = []
    for it in payload or []:
        cats = it.get("categories") or {}
        created = it.get("createdAt")
        out.append(_job(
            board,
            ext_id=it["id"],
            title=it.get("text"),
            company=board.token,
            location=cats.get("location", ""),
            remote=(it.get("workplaceType") == "remote") or "remote" in (cats.get("location") or "").lower(),
            description=it.get("descriptionPlain") or it.get("description"),
            apply_url=it.get("applyUrl") or it.get("hostedUrl"),
            posted_at=datetime.fromtimestamp(created / 1000, timezone.utc).isoformat() if created else "",
            tags=[cats.get("team"), cats.get("commitment")],
        ))
    return out


def _ashby(board: Board, payload: dict) -> list[dict]:
    out = []
    for it in payload.get("jobs", []):
        if it.get("isListed") is False:
            continue
        out.append(_job(
            board,
            ext_id=it["id"],
            title=it.get("title"),
            company=board.token,
            location=it.get("location", ""),
            remote=it.get("isRemote") or it.get("workplaceType") == "Remote",
            description=it.get("descriptionPlain") or it.get("descriptionHtml"),
            apply_url=it.get("applyUrl") or it.get("jobUrl"),
            posted_at=it.get("publishedAt"),
            tags=[it.get("department"), it.get("employmentType")],
        ))
    return out


_ADAPTERS: dict[str, tuple[str, Callable[[Board, object], list[dict]]]] = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true", _greenhouse),
    "lever": ("https://api.lever.co/v0/postings/{token}?mode=json", _lever),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{token}", _ashby),
}


def _term_regex(terms: Iterable[str]) -> re.Pattern | None:
    terms = [t.strip() for t in terms if t and t.strip()]
    if not terms:
        return None
    # Lookarounds instead of \b so terms like "c++" or ".net" still match.
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in terms) + r")(?!\w)", re.I)


def _matches(job: dict, include: re.Pattern, exclude: re.Pattern | None, location: str | None) -> bool:
    haystack = f"{job['title']} {' '.join(job['tags'])}"
    if not include.search(haystack):
        return False
    if exclude and exclude.search(job["title"]):
        return False
    if location:
        loc = location.strip().lower()
        if loc == "remote":
            return bool(job["remote"])
        return loc in job["location"].lower() or bool(job["remote"])
    return True


def _backoff(attempt: int, retry_after: str | None) -> float:
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), 30.0)
    return min(2 ** attempt + random.random(), 30.0)


class AutoSearch:
    """Concurrently queries configured ATS boards and filters by dynamic keywords."""

    def __init__(self, boards: list[Board] | None = None, *, concurrency: int = 6,
                 timeout: float = 20.0, retries: int = 3):
        self.boards = boards if boards is not None else [Board.parse(s) for s in settings.ats_boards]
        self.concurrency = concurrency
        self.timeout = timeout
        self.retries = retries

    async def _get_json(self, client: httpx.AsyncClient, url: str):
        for attempt in range(self.retries + 1):
            try:
                resp = await client.get(url)
            except httpx.TransportError:
                if attempt >= self.retries:
                    raise
                await asyncio.sleep(_backoff(attempt, None))
                continue
            if resp.status_code in _RETRY_STATUS and attempt < self.retries:
                await asyncio.sleep(_backoff(attempt, resp.headers.get("Retry-After")))
                continue
            resp.raise_for_status()
            return resp.json()

    async def _fetch_board(self, client, sem: asyncio.Semaphore, board: Board) -> list[dict] | Exception:
        async with sem:
            try:
                return board.parse_payload(await self._get_json(client, board.url))
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                log.warning("Auto-search failed for %s: %s", board.key, exc)
                return exc

    async def search(self, keywords: Iterable[str], *, exclude: Iterable[str] = (),
                     location: str | None = None) -> dict:
        include = _term_regex(keywords)
        if include is None:
            raise ValueError("At least one keyword is required.")
        exclude_re = _term_regex(exclude)

        sem = asyncio.Semaphore(self.concurrency)
        async with httpx.AsyncClient(timeout=self.timeout, headers=_HEADERS, follow_redirects=True) as client:
            results = await asyncio.gather(*(self._fetch_board(client, sem, b) for b in self.boards))

        jobs: list[dict] = []
        per_board: dict[str, int] = {}
        errors: dict[str, str] = {}
        for board, res in zip(self.boards, results):
            if isinstance(res, Exception):
                errors[board.key] = f"{type(res).__name__}: {res}"
                per_board[board.key] = 0
                continue
            hits = [j for j in res if _matches(j, include, exclude_re, location)]
            per_board[board.key] = len(hits)
            jobs.extend(hits)
        return {"jobs": jobs, "per_board": per_board, "errors": errors}

    async def search_and_store(self, keywords: Iterable[str], **kwargs) -> dict:
        result = await self.search(keywords, **kwargs)
        result["ingested"] = await asyncio.to_thread(upsert_jobs, result["jobs"]) if result["jobs"] else 0
        return result
