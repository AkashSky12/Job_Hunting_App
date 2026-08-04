"""Job ingestion from public sources (RemoteOK, Remotive, and optional Adzuna)."""
from __future__ import annotations

import html
import re

import httpx

from .config import settings
from .db import get_conn

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub(" ", text)).strip()


def fetch_remoteok(limit: int = 60) -> list[dict]:
    """Fetch jobs from RemoteOK's public JSON feed."""
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "AI-Job-Hunter/1.0 (MVP)"}
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    jobs: list[dict] = []
    # First element is metadata/legal notice; skip it.
    for item in payload[1:]:
        ext_id = str(item.get("id") or item.get("slug") or "")
        if not ext_id:
            continue
        jobs.append(
            {
                "id": f"remoteok:{ext_id}",
                "source": "remoteok",
                "external_id": ext_id,
                "title": _clean(item.get("position")),
                "company": _clean(item.get("company")),
                "location": _clean(item.get("location")) or "Remote",
                "remote": 1,
                "salary_min": item.get("salary_min") or None,
                "salary_max": item.get("salary_max") or None,
                "description": _clean(item.get("description"))[:6000],
                "tags": item.get("tags") or [],
                "apply_url": item.get("apply_url") or item.get("url") or "",
                "posted_at": item.get("date") or "",
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def fetch_remotive(limit: int = 60) -> list[dict]:
    """Fetch jobs from Remotive's public JSON API (no key required)."""
    url = "https://remotive.com/api/remote-jobs"
    headers = {"User-Agent": "AI-Job-Hunter/1.0 (MVP)"}
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    jobs: list[dict] = []
    for item in payload.get("jobs", []):
        ext_id = str(item.get("id") or "")
        if not ext_id:
            continue
        salary = _clean(item.get("salary"))
        jobs.append(
            {
                "id": f"remotive:{ext_id}",
                "source": "remotive",
                "external_id": ext_id,
                "title": _clean(item.get("title")),
                "company": _clean(item.get("company_name")),
                "location": _clean(item.get("candidate_required_location")) or "Remote",
                "remote": 1,
                "salary_min": None,
                "salary_max": None,
                "description": (_clean(item.get("description")) + (f" | Salary: {salary}" if salary else ""))[:6000],
                "tags": item.get("tags") or [],
                "apply_url": item.get("url") or "",
                "posted_at": item.get("publication_date") or "",
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def fetch_adzuna(limit: int = 50) -> list[dict]:
    """Fetch jobs from Adzuna. No-op (returns []) unless credentials are set."""
    if not settings.adzuna_enabled:
        return []
    country = settings.adzuna_country
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(limit, 50),
        "what": settings.adzuna_query,
        "content-type": "application/json",
    }
    headers = {"User-Agent": "AI-Job-Hunter/1.0 (MVP)"}
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    jobs: list[dict] = []
    for item in payload.get("results", []):
        ext_id = str(item.get("id") or "")
        if not ext_id:
            continue
        loc = ((item.get("location") or {}).get("display_name")) or "Unknown"
        company = ((item.get("company") or {}).get("display_name")) or "Unknown"
        jobs.append(
            {
                "id": f"adzuna:{ext_id}",
                "source": "adzuna",
                "external_id": ext_id,
                "title": _clean(item.get("title")),
                "company": _clean(company),
                "location": _clean(loc),
                "remote": 1 if "remote" in (loc + item.get("title", "")).lower() else 0,
                "salary_min": int(item["salary_min"]) if item.get("salary_min") else None,
                "salary_max": int(item["salary_max"]) if item.get("salary_max") else None,
                "description": _clean(item.get("description"))[:6000],
                "tags": [item.get("category", {}).get("label")] if item.get("category") else [],
                "apply_url": item.get("redirect_url") or "",
                "posted_at": item.get("created") or "",
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def fetch_jsearch(limit: int = 50) -> list[dict]:
    """Fetch aggregated jobs via JSearch (RapidAPI).

    JSearch aggregates listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter,
    and other boards through Google for Jobs. No-op unless RAPIDAPI_KEY is set.
    """
    if not settings.jsearch_enabled:
        return []
    url = f"https://{settings.jsearch_host}/search"
    params = {
        "query": f"{settings.job_query} in {settings.job_location}",
        "page": "1",
        "num_pages": "1",
    }
    headers = {
        "X-RapidAPI-Key": settings.rapidapi_key or "",
        "X-RapidAPI-Host": settings.jsearch_host,
        "User-Agent": "AI-Job-Hunter/1.0 (MVP)",
    }
    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    jobs: list[dict] = []
    for item in payload.get("data", []) or []:
        ext_id = str(item.get("job_id") or "")
        if not ext_id:
            continue
        city = item.get("job_city") or ""
        country = item.get("job_country") or ""
        location = ", ".join(p for p in (city, country) if p) or "Unknown"
        publisher = item.get("job_publisher") or "aggregator"
        jobs.append(
            {
                "id": f"jsearch:{ext_id}",
                "source": f"jsearch:{publisher.lower()}",
                "external_id": ext_id,
                "title": _clean(item.get("job_title")),
                "company": _clean(item.get("employer_name")) or "Unknown",
                "location": _clean(location),
                "remote": 1 if item.get("job_is_remote") else 0,
                "salary_min": item.get("job_min_salary"),
                "salary_max": item.get("job_max_salary"),
                "description": _clean(item.get("job_description"))[:6000],
                "tags": [publisher],
                "apply_url": item.get("job_apply_link") or "",
                "posted_at": item.get("job_posted_at_datetime_utc") or "",
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def upsert_jobs(jobs: list[dict]) -> int:
    import json

    count = 0
    with get_conn() as conn:
        for job in jobs:
            conn.execute(
                """
                INSERT INTO jobs (id, source, external_id, title, company, location,
                    remote, salary_min, salary_max, description, tags, apply_url, posted_at)
                VALUES (:id, :source, :external_id, :title, :company, :location,
                    :remote, :salary_min, :salary_max, :description, :tags, :apply_url, :posted_at)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, company=excluded.company,
                    location=excluded.location, description=excluded.description,
                    tags=excluded.tags, apply_url=excluded.apply_url
                """,
                {**job, "tags": json.dumps(job["tags"])},
            )
            count += 1
    return count


def ingest() -> int:
    """Fetch + store jobs from all enabled API sources.

    Each source is fetched independently so one failing source does not
    block the others. Returns the number of jobs ingested.
    """
    return ingest_detailed()["total"]


def ingest_detailed() -> dict:
    """Like ``ingest`` but returns per-source counts and errors."""
    fetchers = {
        "remoteok": fetch_remoteok,
        "remotive": fetch_remotive,
        "adzuna": fetch_adzuna,
        "jsearch": fetch_jsearch,
    }
    jobs: list[dict] = []
    per_source: dict[str, int] = {}
    errors: dict[str, str] = {}
    for name, fetch in fetchers.items():
        try:
            fetched = fetch()
            per_source[name] = len(fetched)
            jobs.extend(fetched)
        except Exception as exc:  # network / source errors are non-fatal
            errors[name] = str(exc)
            per_source[name] = 0
    total = upsert_jobs(jobs) if jobs else 0
    return {"total": total, "per_source": per_source, "errors": errors}

