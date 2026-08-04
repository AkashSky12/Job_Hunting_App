# AI Job Hunter — Android App

A native Android client (Kotlin + Jetpack Compose + Material 3) for the
AI Job Hunter FastAPI backend in the repo root. It mirrors the web dashboard:

- **Overview** — KPI cards + a 30-day activity trend chart (applied / interviews / offers)
- **Matches** — ranked job feed with match %, auto-apply, and open-in-browser
- **Applications** — status tracker with forward/back moves through the pipeline
- **Inbox** — paste a recruiter email to classify and auto-update an application
- **Profile** — upload a CV (PDF/DOCX/TXT) and view the parsed profile

## Architecture

```
MainActivity → JobHunterApp (bottom-nav Scaffold)
                 └── OverviewScreen / MatchesScreen / ApplicationsScreen / InboxScreen / ProfileScreen
                        └── AppViewModel (StateFlow) → Network (Retrofit) → FastAPI backend
```

- **UI**: Jetpack Compose, Material 3, Navigation-Compose, a Canvas line chart (no chart lib).
- **State**: single `AppViewModel` exposing an immutable `UiState` via `StateFlow`.
- **Networking**: Retrofit + Gson + OkHttp logging; multipart CV upload via OkHttp.

## Prerequisites

1. **Run the backend first** (from the repo root):
   ```bash
   cd ../../                       # repo root: Job_Search_App/
   .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. **Android Studio** (Koala or newer) with Android SDK 34.

## Configure the backend URL

`app/build.gradle.kts` sets:

```kotlin
buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000/\"")
```

- `10.0.2.2` is the Android **emulator's** alias for your host machine's `localhost`.
- For a **physical device**, change it to your machine's LAN IP (e.g.
  `http://192.168.1.20:8000/`) and add that IP to
  `app/src/main/res/xml/network_security_config.xml`. Ensure phone and computer
  share the same network and the backend binds `--host 0.0.0.0`.

## Build & run

Open this folder (`Mobile_App/Android_App`) in Android Studio and press **Run**,
or from the command line once the Gradle wrapper exists:

```bash
./gradlew installDebug     # build + install on a running emulator/device
```

> **Note on the Gradle wrapper:** this scaffold ships the wrapper *config*
> (`gradle/wrapper/gradle-wrapper.properties`) but not the binary
> `gradle-wrapper.jar`. Opening the project in Android Studio generates it
> automatically. To generate it from the CLI instead, run `gradle wrapper`
> (requires a local Gradle 8.9+ install).

## Tech stack

| Layer | Choice |
|---|---|
| Language | Kotlin 2.0.20 |
| UI | Jetpack Compose + Material 3 (BOM 2024.09.02) |
| Navigation | navigation-compose 2.8.1 |
| Networking | Retrofit 2.11 + Gson + OkHttp logging |
| Async | Kotlin coroutines |
| Min / Target SDK | 24 / 34 |
| Gradle / AGP | 8.9 / 8.5.2 |

## API endpoints consumed

`GET /api/stats`, `GET /api/stats/trend`, `GET /api/matches`,
`GET /api/applications`, `GET /api/profile`, `POST /api/jobs/ingest`,
`POST /api/match`, `POST /api/applications`, `PATCH /api/applications/status`,
`POST /api/inbox/classify`, `POST /api/profile/upload`.
