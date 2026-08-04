# AI-Automated Job Hunting Portal — Complete Build Guide

A step-by-step blueprint to build a full-stack, AI-powered job hunting portal that:
- Parses your CV
- Matches jobs to your profile using AI
- Auto-applies where possible
- Tracks the entire application lifecycle
- Presents everything in a modern, delightful dashboard

---

## 1. High-Level Architecture

```mermaid
flowchart LR
    A[User Uploads CV] --> B[CV Parser Service]
    B --> C[Profile Vector Store]
    D[Job Scrapers / APIs] --> E[Job Ingestion Pipeline]
    E --> F[Job Vector Store]
    C --> G[AI Matching Engine]
    F --> G
    G --> H[Ranked Job Feed]
    H --> I[Auto-Apply Bot]
    I --> J[Application Tracker DB]
    J --> K[Dashboard UI]
    K --> L[Notifications / Email / Slack]
```

**Core services**
1. **Frontend (Dashboard)** — Next.js 14 + Tailwind + shadcn/ui + Framer Motion
2. **Backend API** — FastAPI (Python) or NestJS (Node)
3. **AI Layer** — OpenAI / Anthropic / local LLM (Ollama) + embeddings
4. **Automation Layer** — Playwright for auto-apply & scraping
5. **Database** — PostgreSQL + pgvector (or Supabase)
6. **Queue** — Redis + Celery / BullMQ for background jobs
7. **Storage** — S3 / Supabase Storage for CVs & cover letters
8. **Auth** — Clerk / Auth.js / Supabase Auth

---

## 2. Tech Stack (Recommended)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router), TypeScript | SSR, great DX |
| UI Kit | Tailwind CSS + shadcn/ui + Radix | Beautiful, accessible |
| Animations | Framer Motion | Smooth micro-interactions |
| Charts | Recharts / Tremor | Dashboard visuals |
| Backend | FastAPI + Pydantic v2 | Async, typed, fast |
| DB | PostgreSQL + pgvector | Relational + vector search |
| ORM | SQLAlchemy 2.0 / Prisma | Type-safe |
| Queue | Celery + Redis | Background auto-apply |
| AI | OpenAI GPT-4o + `text-embedding-3-large` | Best matching quality |
| Scraping | Playwright + Scrapy | JS-heavy sites |
| Auth | Clerk (fastest) or Auth.js | Social + magic link |
| Hosting | Vercel (FE) + Railway/Fly.io (BE) | Zero-config |
| Monitoring | Sentry + PostHog | Errors + product analytics |

---

## 3. Project Setup

### 3.1 Create the monorepo

```bash
mkdir ai-job-hunter && cd ai-job-hunter
mkdir apps packages
# Frontend
npx create-next-app@latest apps/web --typescript --tailwind --app --eslint
# Backend
mkdir apps/api && cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary pgvector \
            celery redis pydantic-settings python-multipart \
            openai anthropic playwright pypdf python-docx tiktoken
playwright install chromium
```

### 3.2 Environment variables (`.env`)

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/jobhunter
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
CLERK_SECRET_KEY=sk_...
S3_BUCKET=jobhunter-cvs
SENTRY_DSN=...
```

---

## 4. Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  cv_url TEXT,
  parsed_json JSONB,               -- structured CV
  summary TEXT,                    -- LLM-generated
  target_roles TEXT[],
  target_locations TEXT[],
  min_salary INT,
  work_mode TEXT,                  -- remote / hybrid / onsite
  embedding VECTOR(3072),          -- text-embedding-3-large
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT,                     -- linkedin, indeed, wellfound, etc.
  external_id TEXT UNIQUE,
  title TEXT,
  company TEXT,
  location TEXT,
  remote BOOLEAN,
  salary_min INT, salary_max INT,
  description TEXT,
  requirements TEXT[],
  apply_url TEXT,
  posted_at TIMESTAMPTZ,
  embedding VECTOR(3072),
  raw JSONB
);
CREATE INDEX ON jobs USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  job_id UUID REFERENCES jobs(id),
  score NUMERIC(4,3),              -- 0.000 - 1.000
  reasoning TEXT,                  -- LLM explanation
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, job_id)
);

CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  job_id UUID REFERENCES jobs(id),
  status TEXT,                     -- queued, applied, viewed, interview, offer, rejected
  applied_at TIMESTAMPTZ,
  cover_letter TEXT,
  tailored_cv_url TEXT,
  events JSONB DEFAULT '[]',       -- timeline
  notes TEXT
);
```

---

## 5. CV Parsing Pipeline

### 5.1 Extract text
```python
# apps/api/services/cv_parser.py
from pypdf import PdfReader
from docx import Document

def extract_text(path: str) -> str:
    if path.endswith(".pdf"):
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if path.endswith(".docx"):
        return "\n".join(p.text for p in Document(path).paragraphs)
    raise ValueError("Unsupported CV format")
```

### 5.2 Structure with LLM
```python
from openai import OpenAI
import json
client = OpenAI()

SCHEMA_PROMPT = """Extract the CV into JSON:
{
  "name": str, "email": str, "phone": str,
  "summary": str,
  "skills": [str],
  "experience": [{"company": str, "role": str, "start": str, "end": str, "highlights": [str]}],
  "education": [{"school": str, "degree": str, "year": str}],
  "target_roles": [str]
}
Return ONLY valid JSON."""

def parse_cv(text: str) -> dict:
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SCHEMA_PROMPT},
                  {"role": "user", "content": text}],
    )
    return json.loads(r.choices[0].message.content)
```

### 5.3 Create profile embedding
```python
def embed(text: str) -> list[float]:
    r = client.embeddings.create(model="text-embedding-3-large", input=text)
    return r.data[0].embedding
```

---

## 6. Job Ingestion

### 6.1 Sources
- **APIs**: LinkedIn Jobs API (partner), Adzuna, Reed, Greenhouse Board, Lever, Ashby, USAJobs, RemoteOK, Remotive
- **Scrapers**: Playwright for LinkedIn, Indeed, Wellfound, YCombinator Work-at-a-Startup

> **Legal note**: Always respect `robots.txt`, ToS, and rate limits. Prefer official APIs and public job boards. Scraping LinkedIn may violate their ToS — use partner APIs or user-authorized flows.

### 6.2 Example scraper (RemoteOK — public API)
```python
import httpx
async def fetch_remoteok():
    r = httpx.get("https://remoteok.com/api", headers={"User-Agent": "JobHunter/1.0"})
    for item in r.json()[1:]:
        yield {
            "source": "remoteok",
            "external_id": str(item["id"]),
            "title": item.get("position"),
            "company": item.get("company"),
            "location": item.get("location") or "Remote",
            "remote": True,
            "description": item.get("description", ""),
            "apply_url": item.get("apply_url") or item.get("url"),
        }
```

### 6.3 Celery task
```python
@celery.task
def ingest_jobs():
    for job in fetch_remoteok():
        job["embedding"] = embed(f"{job['title']} {job['description']}")
        upsert_job(job)
```

Schedule with Celery Beat every 30 min.

---

## 7. AI Matching Engine

### 7.1 Hybrid: vector + LLM reranker

```python
def match_jobs(user_id: str, top_k: int = 50):
    profile = db.get_profile(user_id)
    # Stage 1: vector recall
    candidates = db.execute("""
      SELECT id, title, company, description,
             1 - (embedding <=> :emb) AS similarity
      FROM jobs
      WHERE posted_at > now() - interval '14 days'
      ORDER BY embedding <=> :emb
      LIMIT :k
    """, {"emb": profile.embedding, "k": top_k * 3})

    # Stage 2: LLM rerank + reasoning
    ranked = []
    for c in candidates:
        prompt = f"""Rate 0-1 how well this candidate fits the job.
        Candidate: {profile.summary}
        Skills: {profile.parsed_json['skills']}
        Job: {c.title} @ {c.company}
        JD: {c.description[:2000]}
        Return JSON: {{"score": float, "reasoning": str, "red_flags": [str]}}"""
        resp = llm_json(prompt)
        ranked.append((c.id, resp["score"], resp["reasoning"]))
    ranked.sort(key=lambda x: -x[1])
    save_matches(user_id, ranked[:top_k])
```

### 7.2 Score weighting
`final = 0.5 * semantic + 0.3 * llm_score + 0.1 * salary_fit + 0.1 * location_fit`

---

## 8. Auto-Apply Bot

### 8.1 Strategy
1. **One-click boards** (Greenhouse, Lever, Ashby, Workable): use their public JSON endpoints
2. **LinkedIn Easy Apply**: Playwright with the user's own session cookie (user-authorized)
3. **Everything else**: Generate tailored cover letter + CV, then email or open in browser for user review

### 8.2 Tailor CV & cover letter per job

```python
COVER_PROMPT = """Write a concise (180 words) cover letter.
Tone: confident, specific, no clichés.
Candidate: {profile}
Job: {job}
Highlight the top 3 matching achievements."""
```

### 8.3 Playwright apply (Greenhouse example)

```python
from playwright.async_api import async_playwright

async def apply_greenhouse(job_url, profile, cv_path, cover_letter):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page()
        await page.goto(job_url)
        await page.fill('input[name="first_name"]', profile["first_name"])
        await page.fill('input[name="last_name"]', profile["last_name"])
        await page.fill('input[name="email"]', profile["email"])
        await page.set_input_files('input[type="file"][name="resume"]', cv_path)
        await page.fill('textarea[name="cover_letter"]', cover_letter)
        await page.click('button[type="submit"]')
        await page.wait_for_selector("text=Application submitted")
        await b.close()
```

### 8.4 Safety rails
- **Daily cap** (e.g. 20 apps/day)
- **Human-in-the-loop mode**: queue → user approves → submit
- **Blocklist** companies / recruiters
- **Duplicate detection** (never apply to the same job twice)

---

## 9. Application Tracking

### 9.1 Status pipeline
`queued → applied → viewed → phone_screen → interview → offer → accepted/rejected/ghosted`

### 9.2 Auto-update sources
- **Gmail API** — parse recruiter emails, classify with LLM into status events
- **Calendar API** — detect scheduled interviews
- **LinkedIn InMail** — via user OAuth

```python
def classify_email(subject, body):
    return llm_json(f"""Classify this recruiter email.
    Subject: {subject}
    Body: {body[:1500]}
    Return: {{"status": one of [viewed, phone_screen, interview, offer, rejected, other],
              "company": str, "next_action": str, "date": ISO or null}}""")
```

### 9.3 Timeline event
```python
db.applications.update(id=..., events=append({
    "type": "interview_scheduled",
    "at": "2026-08-01T14:00Z",
    "source": "gmail",
    "details": "Technical round with Jane Doe"
}))
```

---

## 10. Dashboard UI/UX

### 10.1 Pages
| Route | Purpose |
|---|---|
| `/` | Overview: KPIs, funnel, upcoming interviews |
| `/matches` | Ranked job feed with match % and reasoning |
| `/applications` | Kanban board (drag between statuses) |
| `/inbox` | Unified email/message thread per application |
| `/profile` | CV upload, target roles, salary, preferences |
| `/settings` | Auto-apply rules, quotas, integrations |

### 10.2 Design system
- **Layout**: sidebar + top bar, max-width 1440
- **Type**: Inter or Geist Sans
- **Color**: neutral base + one accent (e.g. emerald or indigo)
- **Motion**: Framer Motion `layout` transitions on cards; skeleton loaders
- **Density**: comfortable spacing, `rounded-2xl`, subtle shadows
- **Dark mode**: first-class via `next-themes`

### 10.3 Key components (shadcn/ui)
`Card`, `Badge`, `Progress`, `Sheet`, `Dialog`, `DataTable`, `Command` (⌘K), `Toast`, `Tabs`

### 10.4 Match card example (React)

```tsx
// apps/web/components/JobMatchCard.tsx
"use client";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";

export function JobMatchCard({ job }: { job: Match }) {
  return (
    <motion.div layout whileHover={{ y: -2 }}>
      <Card className="rounded-2xl border-muted">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold">{job.title}</h3>
              <p className="text-sm text-muted-foreground">
                {job.company} · {job.location}
              </p>
            </div>
            <Badge variant="secondary">{Math.round(job.score * 100)}% match</Badge>
          </div>
          <Progress value={job.score * 100} className="h-1.5" />
          <p className="text-sm line-clamp-2">{job.reasoning}</p>
          <div className="flex gap-2">
            <Button size="sm">Auto-apply</Button>
            <Button size="sm" variant="outline">Review</Button>
            <Button size="sm" variant="ghost">Hide</Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
```

### 10.5 Kanban for applications
Use `@dnd-kit/core` — columns per status, drag cards to update.

### 10.6 KPI dashboard (Tremor)

```tsx
import { Card, Metric, Text, AreaChart } from "@tremor/react";

<Card>
  <Text>Applications this week</Text>
  <Metric>{stats.appliedThisWeek}</Metric>
  <AreaChart data={stats.trend} index="date" categories={["applied","interviews"]} />
</Card>
```

### 10.7 UX polish checklist
- ⌘K command palette (search jobs, jump to app)
- Optimistic UI on status changes
- Empty states with illustrations
- Confetti on `offer` status
- Weekly email digest
- Mobile-responsive Kanban → vertical stack

---

## 11. Notifications
- **Email**: Resend / Postmark — daily digest + interview reminders
- **Push**: Web Push (VAPID) for status changes
- **Slack**: incoming webhook for high-match jobs (≥ 90%)

---

## 12. Security & Privacy

- Encrypt CV & PII at rest (KMS)
- Store third-party OAuth tokens in a secrets vault (HashiCorp Vault / AWS Secrets Manager)
- Rate-limit API endpoints
- CSRF + strict CORS on the dashboard
- Never log full CV content
- GDPR: export & delete-my-data endpoints
- Row-level security in Postgres (Supabase RLS)

---

## 13. Ethics & Compliance

- **Respect platform ToS**. LinkedIn auto-apply at scale can get accounts banned.
- **Quality > quantity**: 10 great tailored apps beat 200 spammy ones.
- **Transparency**: clearly disclose AI-generated cover letters if asked.
- **User consent**: always keep an approval mode by default.

---

## 14. Development Roadmap

| Phase | Duration | Deliverables |
|---|---|---|
| **MVP** | 2 weeks | CV upload → parse → match against RemoteOK → dashboard feed |
| **v0.2** | +1 week | Application tracker + manual status updates |
| **v0.3** | +2 weeks | Auto-apply for Greenhouse/Lever + tailored cover letters |
| **v0.4** | +1 week | Gmail integration for status auto-updates |
| **v0.5** | +2 weeks | Full Kanban, analytics, notifications, mobile |
| **v1.0** | +1 week | Auth, billing, polish, deploy |

---

## 15. Local Run Commands

```bash
# 1. Infra
docker compose up -d postgres redis

# 2. Backend
cd apps/api
alembic upgrade head
uvicorn main:app --reload --port 8000
celery -A worker worker -l info
celery -A worker beat -l info

# 3. Frontend
cd apps/web
pnpm install
pnpm dev
```

`docker-compose.yml`:
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: jobhunter
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes: { pgdata: {} }
```

---

## 16. Deployment

- **Frontend** → Vercel (`vercel deploy`)
- **Backend + Worker** → Railway / Fly.io / Render
- **Database** → Neon / Supabase / RDS (with pgvector)
- **Object storage** → Cloudflare R2 / S3
- **CI/CD** → GitHub Actions: lint, test, migrate, deploy

---

## 17. Nice-to-Have Enhancements

- 🎙️ **Interview coach**: LLM mock interviews with voice (Whisper + TTS)
- 📊 **Salary negotiator**: benchmark from Levels.fyi + LLM script
- 🧭 **Career path advisor**: skill-gap analysis vs. dream roles
- 🕵️ **Recruiter CRM**: track people, not just companies
- 🌐 **Chrome extension**: one-click "save this job" from any site
- 🧠 **Fine-tune** a small model on your own successful applications

---

## 18. Minimal File Tree

```
ai-job-hunter/
├── apps/
│   ├── web/                    # Next.js dashboard
│   │   ├── app/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── matches/page.tsx
│   │   │   │   ├── applications/page.tsx
│   │   │   │   └── profile/page.tsx
│   │   │   └── api/
│   │   ├── components/
│   │   └── lib/
│   └── api/                    # FastAPI backend
│       ├── main.py
│       ├── models/
│       ├── routers/
│       │   ├── profile.py
│       │   ├── jobs.py
│       │   ├── matches.py
│       │   └── applications.py
│       ├── services/
│       │   ├── cv_parser.py
│       │   ├── matcher.py
│       │   ├── auto_apply.py
│       │   └── email_classifier.py
│       ├── scrapers/
│       └── worker.py           # Celery
├── packages/
│   └── shared-types/           # TS types shared FE/BE
├── docker-compose.yml
└── README.md
```

---

## 19. Getting Started TL;DR

1. `docker compose up -d` → Postgres + Redis
2. Scaffold Next.js (`apps/web`) + FastAPI (`apps/api`)
3. Add Clerk auth → protect `/dashboard`
4. Build CV upload → parse → embed → store profile
5. Ingest RemoteOK jobs → embed → store
6. Vector search + LLM rerank → `/matches` page
7. Kanban → `/applications` page
8. Add Greenhouse auto-apply
9. Gmail webhook → status auto-updates
10. Polish, deploy, iterate

---

**You now have a full blueprint.** Start with the MVP (steps 1–6), ship it to yourself, and only add auto-apply once your matching quality feels right. Quality of matches is the moat — invest most effort there.
