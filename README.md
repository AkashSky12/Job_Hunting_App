# AI Job Hunter — MVP

A runnable, self-contained MVP distilled from `jobhunting.md`. It covers the
blueprint's core loop (steps 1–7): **CV upload → parse → ingest jobs → AI match
→ ranked dashboard feed → auto-apply + application tracker** — with **zero
required infrastructure**.

## What's different from the full blueprint

The blueprint targets a production monorepo (Next.js + FastAPI + Postgres/pgvector
+ Redis/Celery + Playwright + Clerk). To make something that **runs immediately**,
this MVP substitutes:

| Blueprint | MVP |
|---|---|
| Postgres + pgvector | SQLite (`jobhunter.db`) |
| Redis + Celery | synchronous ingestion/matching |
| Next.js dashboard | single-page dashboard served by FastAPI (Tailwind CDN) |
| OpenAI (required) | **optional** — TF-IDF matcher + heuristic CV parser fallback |
| Playwright auto-apply | tailored cover-letter generation + tracker (safe, no ToS risk) |

Job source: **RemoteOK + Remotive public APIs** (legal-safe sources; no keys required).

## Run

```bash
cd /Users/akash/Sky/My_Apps/Job_Search_App
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

Then: **Profile → upload CV** → **Ingest jobs** → **Run matching** → **Matches / Applications**.

Dashboard features: KPI counters + a **30-day activity trend chart** (Chart.js),
a drag-and-drop Kanban tracker, an **Inbox** for email status updates, and a
**⌘K command palette** (Ctrl+K on Windows/Linux) to jump between views, search
jobs, and run actions.

## Run with Docker

```bash
docker compose up --build -d      # http://localhost:8000
docker compose logs -f
```

SQLite persists to the `jobhunter-data` volume. Pass optional keys via a `.env`
file or the shell environment (`OPENAI_API_KEY`, `ADZUNA_*`). Uses
`python:3.12-slim` to guarantee prebuilt wheels.

## Optional: better AI

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` to enable LLM CV parsing,
embedding-based matching, and LLM cover letters. Without it, everything still works
using the built-in TF-IDF matcher.

## Optional integrations

Both are off by default and configured via `.env` (see `.env.example`). The app
runs fully without them.

- **Adzuna jobs** — set `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` (free keys at
  developer.adzuna.com) to add Adzuna listings alongside RemoteOK + Remotive.
- **JSearch aggregator (LinkedIn · Indeed · Glassdoor · ZipRecruiter)** — set
  `RAPIDAPI_KEY` (free tier at rapidapi.com/…/jsearch) to ingest jobs that JSearch
  officially aggregates from those platforms via one legal API.
- **Gmail status auto-updates** — in the **Inbox** tab you can paste a recruiter
  email to auto-classify and advance the matching application (works with no
  setup). For automatic Gmail polling: `pip install google-api-python-client
  google-auth-oauthlib`, drop a Desktop-app `credentials.json` in this folder,
  then click **Sync Gmail** (first run opens a browser to authorize).

## Job sources

The **Sources** tab (web / Android / iOS) lists every platform with live status:

- **Ingested via API** (pulled into your ranked feed): RemoteOK, Remotive,
  Adzuna (key), and JSearch (key — covers LinkedIn, Indeed, Glassdoor, ZipRecruiter).
- **Deep-link search** (opened on the platform, one tap): **LinkedIn, Indeed,
  Naukri, Foundit, JobStreet, Instahyre, Cutshort**. These have no public
  job-search API and scraping them violates their ToS, so the apps build the
  correct search URL for your role/location and open it instead.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/profile/upload` | Upload + parse CV |
| GET | `/api/profile` | Current profile |
| POST | `/api/jobs/ingest` | Pull jobs (RemoteOK + Remotive + Adzuna + JSearch); returns per-source counts |
| GET | `/api/sources` | All job sources + enabled status + deep-link search URLs |
| POST | `/api/match` | Rank jobs vs. profile |
| GET | `/api/matches` | Ranked feed |
| POST | `/api/applications` | Auto-apply (generate cover letter) |
| PATCH | `/api/applications/status` | Move Kanban status |
| POST | `/api/inbox/classify` | Classify a pasted email + auto-update |
| POST | `/api/inbox/gmail-sync` | Pull recent Gmail + auto-update (opt-in) |
| GET | `/api/stats` | KPIs + funnel + feature flags |
| GET | `/api/stats/trend` | Daily applied/interview/offer counts (charted) |

