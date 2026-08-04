# Future Enhancements — KPI Analytics & Docker Deployment

Planning notes for two roadmap items that are **not yet implemented** in the MVP.
Use this as the implementation guide when you pick them up.

> **Update (2026-07):** Both KPI trend charts and Docker deployment have since
> been **implemented** — see `GET /api/stats/trend`, the Overview trend chart in
> `app/static/index.html`, and the root `Dockerfile` / `docker-compose.yml`.
> This document is retained as background/design rationale.

---

## 1. KPI Trend Charts

The Overview page currently shows static KPI counters (`Jobs`, `Matches`,
`Applications`, `Interviews`) and a plain funnel list. The next step is a
time-series **trend chart** so you can see application velocity over time.

### 1.1 Data model change

Add a lightweight daily snapshot table so trends can be computed without
expensive scans:

```sql
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    day TEXT PRIMARY KEY,          -- YYYY-MM-DD
    jobs INTEGER,
    matches INTEGER,
    applied INTEGER,
    interviews INTEGER,
    offers INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Alternatively, derive trends on the fly from existing timestamps
(`applications.applied_at`, `applications.updated_at`, and the `events` JSON
timeline) — no schema change needed for a first pass:

```sql
SELECT date(applied_at) AS day, COUNT(*) AS applied
FROM applications
WHERE applied_at IS NOT NULL
GROUP BY date(applied_at)
ORDER BY day;
```

### 1.2 New endpoint

Add to `app/main.py`:

```python
@app.get("/api/stats/trend")
def stats_trend(days: int = 30):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date(applied_at) AS day, COUNT(*) AS applied
            FROM applications
            WHERE applied_at >= date('now', ?)
            GROUP BY date(applied_at) ORDER BY day
            """,
            (f'-{days} days',),
        ).fetchall()
    return [dict(r) for r in rows]
```

Extend the query with `interviews`/`offers` counts derived from the `events`
timeline (parse JSON in Python, or store status-change dates in a flat column).

### 1.3 Frontend chart

The dashboard uses the Tailwind CDN and vanilla JS (no build step), so add a
tiny charting lib the same way — via CDN. Recommended: **Chart.js** (single
`<script>` tag, no bundler).

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
```

```html
<!-- in the Overview view, replace/augment the funnel card -->
<div class="rounded-2xl border border-zinc-800 p-5">
  <h3 class="font-medium mb-3">Applications over time</h3>
  <canvas id="trendChart" height="120"></canvas>
</div>
```

```js
let trendChart;
async function loadTrend() {
  const data = await api('/api/stats/trend?days=30');
  const labels = data.map(d => d.day);
  const applied = data.map(d => d.applied);
  const ctx = document.getElementById('trendChart');
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Applied', data: applied,
      borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.15)',
      fill: true, tension: .3 }] },
    options: { plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: '#a1a1aa' } }, y: { ticks: { color: '#a1a1aa' }, beginAtZero: true } } }
  });
}
```

Call `loadTrend()` from inside `loadStats()`.

### 1.4 Nice-to-have KPI additions

- **Conversion rates**: applied → interview %, interview → offer %.
- **Response time**: median days from `applied` to first status change.
- **Source effectiveness**: match/apply/interview counts grouped by
  `jobs.source` (RemoteOK vs Remotive vs Adzuna).
- **Sparklines** on each KPI counter card.

---

## 2. Docker Deployment

Package the FastAPI + SQLite MVP as a single container. SQLite persists to a
mounted volume so data survives restarts.

### 2.1 Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps (lxml for python-docx needs libxml2/libxslt at build time only
# when wheels are unavailable; slim wheels usually suffice).
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Data dir for the SQLite file (mounted as a volume in compose).
ENV DATABASE_PATH=/data/jobhunter.db
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> Pin to `python:3.12-slim` (not 3.14) to guarantee prebuilt wheels for
> `pydantic-core`, `lxml`, etc. — avoids the Rust build issue hit during local
> setup.

### 2.2 .dockerignore

Create `.dockerignore` to keep the image small and secrets out:

```
.venv/
__pycache__/
*.pyc
jobhunter.db
.env
token.json
credentials.json
docs/
*.md
```

### 2.3 docker-compose.yml

```yaml
services:
  jobhunter:
    build: .
    ports:
      - "8000:8000"
    environment:
      # All optional — omit to run in zero-config fallback mode.
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ADZUNA_APP_ID: ${ADZUNA_APP_ID:-}
      ADZUNA_APP_KEY: ${ADZUNA_APP_KEY:-}
      DATABASE_PATH: /data/jobhunter.db
    volumes:
      - jobhunter-data:/data
    restart: unless-stopped

volumes:
  jobhunter-data:
```

### 2.4 Build & run

```bash
# With compose (recommended)
docker compose up --build -d
docker compose logs -f
# open http://localhost:8000

# Or plain docker
docker build -t jobhunter .
docker run -d -p 8000:8000 -v jobhunter-data:/data \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" jobhunter
```

### 2.5 Notes & gotchas

- **Secrets**: never bake `.env`, `token.json`, or `credentials.json` into the
  image — they're excluded via `.dockerignore` and passed at runtime instead.
- **Gmail sync in a container**: the OAuth `run_local_server()` flow needs a
  browser and can't complete headless. Authorize once locally to generate
  `token.json`, then mount it read-only:
  `-v $PWD/token.json:/data/token.json:ro` and set
  `GMAIL_TOKEN_PATH=/data/token.json`.
- **Migrating to Postgres later**: the blueprint's production target is
  Postgres + pgvector. When ready, swap `app/db.py` for SQLAlchemy + a
  `postgres` compose service and move embeddings into a `VECTOR` column.
- **Health check**: add a `GET /health` route returning `{"ok": true}` and wire
  a compose `healthcheck` for orchestrators.

### 2.6 Deploying to a cloud host

Any container host works. Quick options:

| Target | How |
|---|---|
| Azure Container Apps | `az containerapp up --source .` (see the `azure-prepare` skill) |
| Fly.io | `fly launch` → `fly deploy` (add a volume for `/data`) |
| Render / Railway | Connect repo, set env vars, attach a persistent disk at `/data` |

For a managed database and object storage (CVs, cover letters), follow the
production stack in `../jobhunting.md` §16.
```
