"""Job source registry.

Two kinds of sources:

* ``api``     — legally ingestable feeds/APIs. Their listings are pulled into the
                local database (RemoteOK, Remotive, Adzuna, and the JSearch
                aggregator which officially covers LinkedIn / Indeed / Glassdoor /
                ZipRecruiter via one RapidAPI key).
* ``deeplink`` — platforms without a public job-search API (LinkedIn, Naukri,
                Foundit, JobStreet, Indeed, Instahyre, Cutshort). We do NOT scrape
                these (against their ToS); instead we build the correct search URL
                for the user's role/location so the app can open it in one tap.

This keeps the integration honest, legal, and robust across web, Android, and iOS.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from .config import settings


@dataclass
class SourceInfo:
    key: str
    name: str
    kind: str            # "api" | "deeplink"
    enabled: bool
    note: str
    search_url: str | None = None


def _slug(text: str) -> str:
    return "-".join(text.lower().split())


def _deeplink_url(key: str, query: str, location: str) -> str:
    q = query.strip() or settings.job_query
    loc = location.strip() or settings.job_location
    qe, le = quote_plus(q), quote_plus(loc)
    qs, ls = _slug(q), _slug(loc)
    templates = {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={qe}&location={le}",
        "indeed": f"https://www.indeed.com/jobs?q={qe}&l={le}",
        "naukri": f"https://www.naukri.com/{qs}-jobs-in-{ls}",
        "foundit": f"https://www.foundit.in/srp/results?query={qe}&locations={le}",
        "jobstreet": f"https://www.jobstreet.com/{qs}-jobs/in-{ls}",
        "instahyre": f"https://www.instahyre.com/search-jobs/?q={qe}",
        "cutshort": f"https://cutshort.io/jobs/{qs}-jobs",
    }
    return templates[key]


# Platforms exposed as deep-link searches (no public API / scraping prohibited).
DEEPLINK_SOURCES: dict[str, str] = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "naukri": "Naukri",
    "foundit": "Foundit",
    "jobstreet": "JobStreet",
    "instahyre": "Instahyre",
    "cutshort": "Cutshort",
}


def list_sources(query: str = "", location: str = "") -> list[SourceInfo]:
    """Return all sources with live enabled-status and resolved deep links."""
    q = query or settings.job_query
    loc = location or settings.job_location

    api_sources = [
        SourceInfo("remoteok", "RemoteOK", "api", True, "Public API — no key required."),
        SourceInfo("remotive", "Remotive", "api", True, "Public API — no key required."),
        SourceInfo(
            "adzuna", "Adzuna", "api", settings.adzuna_enabled,
            "Set ADZUNA_APP_ID / ADZUNA_APP_KEY to enable.",
        ),
        SourceInfo(
            "jsearch", "JSearch (LinkedIn · Indeed · Glassdoor · ZipRecruiter)", "api",
            settings.jsearch_enabled,
            "Aggregator API. Set RAPIDAPI_KEY to enable.",
        ),
    ]

    deeplink_sources = [
        SourceInfo(
            key, name, "deeplink", True,
            "Opens the platform's job search (no public API available).",
            _deeplink_url(key, q, loc),
        )
        for key, name in DEEPLINK_SOURCES.items()
    ]

    return api_sources + deeplink_sources
