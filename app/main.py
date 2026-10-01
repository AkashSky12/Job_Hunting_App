"""AI Job Hunter — FastAPI MVP.

Runs with zero external infra: SQLite for storage, RemoteOK for jobs,
and an optional OpenAI key for higher-quality parsing/matching.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import autoapply, autosearch, cv_parser, email_sync, jobs, matcher, sources
from .config import settings
from .db import get_conn, init_db, row_to_dict

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="AI Job Hunter", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------- Profile ----
@app.post("/api/profile/upload")
async def upload_cv(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        text = cv_parser.extract_text(file.filename or "cv.pdf", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    parsed = cv_parser.parse_cv(text)
    profile_text = cv_parser.flatten_profile_text(parsed)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO profile (id, full_name, email, summary, parsed_json,
                target_roles, profile_text, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                full_name=excluded.full_name, email=excluded.email,
                summary=excluded.summary, parsed_json=excluded.parsed_json,
                target_roles=excluded.target_roles, profile_text=excluded.profile_text,
                updated_at=datetime('now')
            """,
            (
                parsed.get("name", ""),
                parsed.get("email", ""),
                parsed.get("summary", ""),
                json.dumps(parsed),
                json.dumps(parsed.get("target_roles", [])),
                profile_text,
            ),
        )
    return {"ok": True, "profile": parsed, "ai_enabled": settings.ai_enabled}


@app.get("/api/profile")
def get_profile():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return row_to_dict(row) or {}


# ------------------------------------------------------------------- Jobs ----
@app.post("/api/jobs/ingest")
def ingest_jobs():
    try:
        result = jobs.ingest_detailed()
    except Exception as exc:  # network / source errors
        raise HTTPException(502, f"Job ingestion failed: {exc}")
    return {
        "ok": True,
        "ingested": result["total"],
        "per_source": result["per_source"],
        "errors": result["errors"],
    }


class AutoSearchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=20)
    exclude: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = None
    boards: list[str] | None = Field(default=None, max_length=100)


@app.post("/api/jobs/auto-search")
async def auto_search(req: AutoSearchRequest):
    """Keyword search across public Greenhouse/Lever/Ashby boards; stores hits."""
    try:
        boards = [autosearch.Board.parse(b) for b in req.boards] if req.boards else None
        engine = autosearch.AutoSearch(boards)
        if not engine.boards:
            raise ValueError("No boards configured. Set ATS_BOARDS or pass `boards`.")
        result = await engine.search_and_store(req.keywords, exclude=req.exclude, location=req.location)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {
        "ok": True,
        "ingested": result["ingested"],
        "per_board": result["per_board"],
        "errors": result["errors"],
    }


@app.get("/api/sources")
def list_sources(query: str = "", location: str = ""):
    """All job sources with enabled status + deep-link search URLs."""
    return [s.__dict__ for s in sources.list_sources(query, location)]


@app.get("/api/jobs")
def list_jobs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY ingested_at DESC LIMIT 200").fetchall()
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------- Matches ----
@app.post("/api/match")
def run_match():
    with get_conn() as conn:
        has_profile = conn.execute("SELECT 1 FROM profile WHERE id = 1").fetchone()
    if not has_profile:
        raise HTTPException(400, "Upload a CV first.")
    count = matcher.run_matching()
    return {"ok": True, "matched": count}


@app.get("/api/matches")
def list_matches():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT m.score, m.reasoning, j.*, a.status AS app_status
            FROM matches m
            JOIN jobs j ON j.id = m.job_id
            LEFT JOIN applications a ON a.job_id = j.id
            ORDER BY m.score DESC
            """
        ).fetchall()
    return [row_to_dict(r) for r in rows]


# ----------------------------------------------------------- Applications ----
class ApplyRequest(BaseModel):
    job_id: str


class StatusRequest(BaseModel):
    job_id: str
    status: str


VALID_STATUSES = {
    "queued", "applied", "viewed", "phone_screen",
    "interview", "offer", "accepted", "rejected", "ghosted",
}


@app.post("/api/applications")
def create_application(req: ApplyRequest):
    with get_conn() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,)).fetchone()
        if not job:
            raise HTTPException(404, "Job not found")
        profile = row_to_dict(conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()) or {}

    cover = matcher.generate_cover_letter(row_to_dict(job), profile)
    event = json.dumps([{"type": "created", "at": _now()}])
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO applications (job_id, status, cover_letter, events, applied_at, updated_at)
            VALUES (?, 'applied', ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(job_id) DO UPDATE SET
                cover_letter=excluded.cover_letter, updated_at=datetime('now')
            """,
            (req.job_id, cover, event),
        )
    return {"ok": True, "cover_letter": cover}


class AutoApplyRequest(BaseModel):
    job_id: str
    submit: bool = False


_auto_apply_lock = asyncio.Lock()


async def _run_auto_apply(engine: "autoapply.AutoApplyEngine", job_id: str, url: str, submit: bool) -> None:
    async with _auto_apply_lock:
        try:
            result = await engine.apply(url, submit=submit, keep_open=not engine.headless)
        except Exception:
            log.exception("Auto-apply crashed for %s", job_id)
            return
        await asyncio.to_thread(autoapply.record_application, job_id, result)


@app.post("/api/applications/auto-apply", status_code=202)
async def auto_apply(req: AutoApplyRequest, background: BackgroundTasks):
    """Pre-fill the job's application form in a browser on the backend host."""
    with get_conn() as conn:
        job = conn.execute("SELECT apply_url FROM jobs WHERE id = ?", (req.job_id,)).fetchone()
    if not job or not job["apply_url"]:
        raise HTTPException(404, "Job not found or has no apply URL")
    if not settings.resume_path:
        raise HTTPException(400, "Set RESUME_PATH on the backend to enable auto-apply.")
    if _auto_apply_lock.locked():
        raise HTTPException(409, "Another auto-apply session is in progress.")
    try:
        engine = autoapply.AutoApplyEngine(
            autoapply.ApplicantProfile.from_db(), settings.resume_path, headless=settings.autoapply_headless
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc))
    background.add_task(_run_auto_apply, engine, req.job_id, job["apply_url"], req.submit)
    return {"ok": True, "started": True, "headless": engine.headless}


@app.patch("/api/applications/status")
def update_status(req: StatusRequest):
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Use one of {sorted(VALID_STATUSES)}")
    with get_conn() as conn:
        row = conn.execute("SELECT events FROM applications WHERE job_id = ?", (req.job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Application not found")
        events = json.loads(row["events"] or "[]")
        events.append({"type": "status_change", "status": req.status, "at": _now()})
        conn.execute(
            "UPDATE applications SET status = ?, events = ?, updated_at = datetime('now') WHERE job_id = ?",
            (req.status, json.dumps(events), req.job_id),
        )
    return {"ok": True}


@app.get("/api/applications")
def list_applications():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.*, j.title, j.company, j.location, j.apply_url
            FROM applications a JOIN jobs j ON j.id = a.job_id
            ORDER BY a.updated_at DESC
            """
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/stats")
def stats():
    with get_conn() as conn:
        jobs_count = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
        matches_count = conn.execute("SELECT COUNT(*) c FROM matches").fetchone()["c"]
        apps = conn.execute("SELECT status, COUNT(*) c FROM applications GROUP BY status").fetchall()
    funnel = {r["status"]: r["c"] for r in apps}
    return {
        "jobs": jobs_count,
        "matches": matches_count,
        "applications": sum(funnel.values()),
        "funnel": funnel,
        "ai_enabled": settings.ai_enabled,
        "adzuna_enabled": settings.adzuna_enabled,
        "gmail_enabled": settings.gmail_enabled,
    }


@app.get("/api/stats/trend")
def stats_trend(days: int = 30):
    """Daily applied/interview/offer counts over the last N days."""
    from collections import defaultdict
    from datetime import date, timedelta

    applied: dict[str, int] = defaultdict(int)
    interviews: dict[str, int] = defaultdict(int)
    offers: dict[str, int] = defaultdict(int)

    with get_conn() as conn:
        rows = conn.execute("SELECT applied_at, events FROM applications").fetchall()
    for r in rows:
        if r["applied_at"]:
            applied[r["applied_at"][:10]] += 1
        for ev in json.loads(r["events"] or "[]"):
            day = (ev.get("at") or "")[:10]
            if not day:
                continue
            if ev.get("status") == "interview":
                interviews[day] += 1
            elif ev.get("status") == "offer":
                offers[day] += 1

    # Build a continuous date axis so the chart has no gaps.
    today = date.today()
    series = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        series.append(
            {"day": d, "applied": applied[d], "interviews": interviews[d], "offers": offers[d]}
        )
    return series


# --------------------------------------------------------------- Inbox / email
class ClassifyRequest(BaseModel):
    subject: str
    body: str


@app.post("/api/inbox/classify")
def inbox_classify(req: ClassifyRequest):
    """Classify a pasted recruiter email and auto-update the matching app."""
    return email_sync.classify_and_update(req.subject, req.body)


@app.post("/api/inbox/gmail-sync")
def inbox_gmail_sync():
    """Pull recent Gmail messages and auto-update statuses (opt-in)."""
    result = email_sync.sync_gmail()
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Gmail sync unavailable"))
    return result


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------- UI -------
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
