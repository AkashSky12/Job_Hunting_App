"""Email-based application status auto-updates.

Two capabilities:
  1. classify_email() — turn a recruiter email into a status event
     (LLM when OPENAI_API_KEY is set, otherwise keyword heuristics).
  2. sync_gmail() — optionally pull recent messages from Gmail and apply
     classifications. Requires google API libraries + OAuth credentials;
     degrades gracefully with a clear message when not configured.

Matching to an application is done by fuzzy company-name overlap.
"""
from __future__ import annotations

import json
import re

from . import ai
from .config import settings
from .db import get_conn, row_to_dict

VALID = {"viewed", "phone_screen", "interview", "offer", "rejected", "other"}

_HEURISTICS = [
    ("rejected", ["unfortunately", "not moving forward", "other candidates", "will not be proceeding", "regret to inform"]),
    ("offer", ["offer", "pleased to offer", "compensation package", "we would like to offer"]),
    ("interview", ["interview", "technical round", "onsite", "meet the team", "coding challenge"]),
    ("phone_screen", ["phone screen", "quick call", "recruiter call", "initial call", "screening call"]),
    ("viewed", ["received your application", "reviewing your application", "application received", "thanks for applying"]),
]

_CLASSIFY_PROMPT = """Classify this recruiter email into an application status.
Return ONLY JSON: {"status": one of ["viewed","phone_screen","interview","offer","rejected","other"],
"company": string, "next_action": string}"""


def classify_email(subject: str, body: str) -> dict:
    if settings.ai_enabled:
        result = ai.chat_json(_CLASSIFY_PROMPT, f"Subject: {subject}\n\nBody: {body[:2000]}")
        if result and result.get("status") in VALID:
            result.setdefault("company", "")
            result.setdefault("next_action", "")
            return result

    text = f"{subject}\n{body}".lower()
    status = "other"
    for label, keywords in _HEURISTICS:
        if any(k in text for k in keywords):
            status = label
            break
    return {"status": status, "company": _guess_company(subject, body), "next_action": ""}


def _guess_company(subject: str, body: str) -> str:
    # Look for "at <Company>" or "from <Company>" patterns.
    m = re.search(r"\b(?:at|from|with)\s+([A-Z][A-Za-z0-9&.\- ]{2,40})", f"{subject} {body}")
    return m.group(1).strip() if m else ""


def _apply_status_to_company(company: str, status: str, source: str = "email") -> dict | None:
    """Find the best-matching application by company and update its status."""
    if status == "other" or not company:
        return None
    company_l = company.lower()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.job_id, a.events, j.company
            FROM applications a JOIN jobs j ON j.id = a.job_id
            """
        ).fetchall()
        match = None
        for r in rows:
            jc = (r["company"] or "").lower()
            if jc and (jc in company_l or company_l in jc):
                match = r
                break
        if not match:
            return None
        events = json.loads(match["events"] or "[]")
        events.append({"type": "status_change", "status": status, "source": source, "at": _now()})
        conn.execute(
            "UPDATE applications SET status = ?, events = ?, updated_at = datetime('now') WHERE job_id = ?",
            (status, json.dumps(events), match["job_id"]),
        )
    return {"job_id": match["job_id"], "company": match["company"], "status": status}


def classify_and_update(subject: str, body: str) -> dict:
    result = classify_email(subject, body)
    updated = _apply_status_to_company(result.get("company", ""), result["status"])
    return {"classification": result, "updated": updated}


def sync_gmail(max_messages: int = 20) -> dict:
    """Pull recent Gmail messages and auto-update matching applications.

    Requires: pip install google-api-python-client google-auth-oauthlib
    and a Gmail OAuth `credentials.json` (Desktop app) on first run.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return {
            "ok": False,
            "error": "Gmail libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib",
        }

    import os

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    if os.path.exists(settings.gmail_token_path):
        creds = Credentials.from_authorized_user_file(settings.gmail_token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(settings.gmail_credentials_path):
            flow = InstalledAppFlow.from_client_secrets_file(settings.gmail_credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        else:
            return {"ok": False, "error": "No Gmail credentials.json found. See README for setup."}
        with open(settings.gmail_token_path, "w") as fh:
            fh.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    listing = (
        service.users()
        .messages()
        .list(userId="me", q="category:primary newer_than:30d", maxResults=max_messages)
        .execute()
    )
    updates = []
    for meta in listing.get("messages", []):
        msg = service.users().messages().get(userId="me", id=meta["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "")
        snippet = msg.get("snippet", "")
        res = classify_and_update(subject, snippet)
        if res["updated"]:
            updates.append(res["updated"])
    return {"ok": True, "scanned": len(listing.get("messages", [])), "updates": updates}


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
