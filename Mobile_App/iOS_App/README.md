# AI Job Hunter — iOS App

A native iOS client (SwiftUI + Swift Charts) for the AI Job Hunter FastAPI
backend in the repo root. It mirrors the web dashboard and the Android app.

## Features

- **Overview** — KPI cards + a 30-day activity trend chart (Swift Charts)
- **Matches** — ranked job feed with match %, auto-apply, open-in-Safari
- **Apps** — application status tracker with forward/back pipeline moves
- **Inbox** — paste a recruiter email to classify and auto-update an application
- **Profile** — upload a CV (PDF/DOCX/TXT) via the document picker; view parsed profile

## Architecture

```
JobHunterApp (@main)
  └── ContentView (TabView + message banner)
        ├── OverviewView / MatchesView / ApplicationsView / InboxView / ProfileView
        └── AppViewModel (@MainActor ObservableObject, @Published state)
              └── APIClient (async/await URLSession) → FastAPI backend
```

- **UI**: SwiftUI, Swift Charts, `Layout` protocol for chip wrapping, native `.refreshable`.
- **State**: a single `AppViewModel` (`@MainActor`, `ObservableObject`).
- **Networking**: `async/await` `URLSession`; multipart CV upload; typed `Codable` models.
- **Project format**: modern file-system-synchronized group (Xcode 16+), so new
  `.swift` files under `JobHunter/` are picked up automatically — no pbxproj edits.

## Requirements

- **Xcode 16 or newer** (built/verified with Xcode 26, iOS 17+ deployment target).
- The **backend running** on the host (from the repo root):
  ```bash
  cd ../../
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

## Run

1. Open `JobHunter.xcodeproj` in Xcode.
2. Select an iOS Simulator and press **Run** (⌘R).

The iOS Simulator shares the host's network, so the app talks to
`http://127.0.0.1:8000` out of the box (cleartext allowed for localhost via
`Info.plist` App Transport Security exceptions).

### Physical device

Change `baseURL` in `JobHunter/APIClient.swift` to your machine's LAN IP
(e.g. `http://192.168.1.20:8000`) and add that host to the
`NSAppTransportSecurity` exceptions in `JobHunter/Info.plist`. Ensure the phone
and computer share the same network and the backend binds `--host 0.0.0.0`.

## API endpoints consumed

`GET /api/stats`, `GET /api/stats/trend`, `GET /api/matches`,
`GET /api/applications`, `GET /api/profile`, `POST /api/jobs/ingest`,
`POST /api/match`, `POST /api/applications`, `PATCH /api/applications/status`,
`POST /api/inbox/classify`, `POST /api/profile/upload`.

## Project layout

```
iOS_App/
├── JobHunter.xcodeproj/
└── JobHunter/
    ├── JobHunterApp.swift        # @main entry
    ├── ContentView.swift         # TabView + transient message banner
    ├── Models.swift              # Codable API models
    ├── APIClient.swift           # async/await REST + multipart upload
    ├── AppViewModel.swift        # ObservableObject state
    ├── Theme.swift               # palette + helpers
    ├── Info.plist                # ATS localhost exceptions
    ├── Assets.xcassets/          # AppIcon + AccentColor
    └── Views/
        ├── OverviewView.swift
        ├── MatchesView.swift
        ├── ApplicationsView.swift
        ├── InboxView.swift
        └── ProfileView.swift
```
