# CaptureIQ

**CaptureIQ** is a local SBIR/STTR solicitation pipeline application that helps small businesses and research teams track, evaluate, and pursue government funding opportunities. It pulls topics directly from SBIR.gov and DoD SBIR sources, lets your team score and prioritize solicitations, manage proposal projects, and stay organized from discovery through submission.

---

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
  - [Running from Source](#running-from-source)
  - [Running the Desktop App](#running-the-desktop-app)
- [First-Run Setup](#first-run-setup)
- [User Management](#user-management)
- [Using CaptureIQ](#using-captureiq)
  - [Dashboard](#dashboard)
  - [Ingest Data](#ingest-data)
  - [Topics](#topics)
  - [Favorites](#favorites)
  - [Nominated & Passed](#nominated--passed)
  - [Projects](#projects)
  - [Analytics](#analytics)
  - [Google Drive Integration](#google-drive-integration)
- [Data Storage](#data-storage)
- [Distribution](#distribution)
  - [Mac — Apple Silicon (M1–M4)](#mac--apple-silicon-m1m4)
  - [Mac — Intel](#mac--intel)
  - [Windows](#windows)
- [Troubleshooting](#troubleshooting)
- [Building from Source](#building-from-source)

---

## Features

| Feature | Description |
|---|---|
| **SBIR Ingestion** | Pull solicitations directly from SBIR.gov and DoD SBIR sources |
| **Topic Explorer** | Browse, search, filter, and sort all ingested solicitation topics |
| **Favorites** | Star topics you want to revisit later |
| **Nominate / Pass** | Mark topics as Nominated (pursuing) or Passed (not pursuing) |
| **Scoring** | Automatically score topics by relevance based on your pipeline |
| **CSV Export** | Export topic lists to CSV for reporting or offline review |
| **Projects** | Create proposal projects linked to specific solicitations |
| **Project Artifacts** | Upload and store proposal documents inside each project |
| **Analytics** | Charts and insights on your pipeline: agency mix, topic trends, keyword frequency, phase distribution |
| **Multi-User Login** | Secure login for multiple team members; favorites and status are per-user |
| **Admin Panel** | Admin users can create, deactivate, and manage team accounts |
| **Google Drive** | Optionally sync project artifacts to Google Drive |
| **Local & Private** | All data lives on your own machine — nothing is sent to the cloud |

---

## Getting Started

### Running from Source

**Requirements:** Python 3.9+

1. Clone or download this repository.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the app:
   ```bash
   python launcher.py
   ```

   CaptureIQ will start a local server and open your browser automatically at `http://127.0.0.1:5000`.

4. On first launch, you will be directed to create an admin account.

---

### Running the Desktop App

Download the packaged app from the [Releases](https://github.com/ntoscano01/capture-iq/releases) page (no Python required).

| Platform | File |
|---|---|
| Mac (Apple Silicon M1–M4) | `CaptureIQ-mac.zip` |
| Windows | `CaptureIQ-windows.zip` |

See the [Distribution](#distribution) section for detailed install instructions per platform.

---

## First-Run Setup

The very first time CaptureIQ starts with an empty database, it will redirect you to a **Setup** page where you create the admin account.

1. Navigate to `http://127.0.0.1:5000` in your browser (or it opens automatically).
2. You will be taken to `/setup` — fill in a username, optional email, and password.
3. Click **Create Admin Account**.
4. You will be redirected to the login page. Sign in with the credentials you just created.

> **Important:** The setup page is only accessible when no users exist. After the admin account is created, it becomes unavailable.

---

## User Management

CaptureIQ supports multiple users. Each user has their own favorites, nominations, and pass decisions — other team members' choices don't affect your view.

**Admin users** can manage accounts from the sidebar under **Settings → Users**.

### Adding a User

1. Go to **Settings → Users** in the sidebar (admin only).
2. Scroll to the **Add New User** card.
3. Fill in username, email (optional), password, and role (User or Admin).
4. Click **Create User**.

The new user can now log in with those credentials.

### Managing Existing Users

From the Users page, admins can:

- **Deactivate / Reactivate** — Deactivated accounts cannot log in.
- **Reset Password** — Enter a new password for any user.
- **Delete** — Permanently remove an account (cannot delete your own account).

### Roles

| Role | Capabilities |
|---|---|
| **User** | Browse topics, favorites, nominations, projects, analytics, export |
| **Admin** | Everything above + manage users |

---

## Using CaptureIQ

### Dashboard

The Dashboard gives you a quick snapshot of your pipeline:

- Total topics ingested
- How many you've favorited
- How many are nominated (pursuing)
- How many are passed (not pursuing)
- Recent activity

### Ingest Data

Before you can browse topics, you need to pull solicitation data. Go to **Pipeline → Ingest Data** and select a source:

- **SBIR.gov** — current open solicitations from all federal agencies
- **DoD SBIR** — Department of Defense topics

Click **Ingest** and CaptureIQ will download and store the topics locally. You can run ingestion multiple times — it merges new topics without duplicating existing ones.

> Ingestion requires an internet connection. After ingestion, everything else works offline.

### Topics

The **Topics** page shows all ingested solicitation topics with filtering and sorting options:

- **Search** by keyword across topic titles and descriptions
- **Filter** by Agency, Phase, Branch/Component, and Year
- **Sort** by Topic Number, Title, Agency, or Score
- **Favorite** any topic by clicking the ⭐ star icon
- **Nominate or Pass** topics using the status buttons
- **Export to CSV** using the Export button in the top bar

Clicking a topic title opens the full topic detail view.

### Favorites

**Pipeline → Favorites** shows only the topics you've starred. Your favorites are private to your account — each team member maintains their own.

### Nominated & Passed

- **Nominated** — Topics your team (or you) are actively pursuing for a proposal.
- **Passed** — Topics you've reviewed and decided not to pursue.

These filters appear in the sidebar under Pipeline. Like favorites, these are per-user.

### Projects

**Capture → Projects** is where you manage active proposal efforts.

**Creating a Project:**
1. Navigate to a topic's detail page and click **Create Project**, or go to Projects → New Project.
2. Give the project a name, link it to a solicitation topic, and set a due date.

**Inside a Project:**
- Upload proposal artifacts (technical volumes, cost proposals, past performance, etc.)
- Track proposal progress through stages
- Link to Google Drive folders if Drive integration is enabled

### Analytics

**Insights → Analytics** provides charts and statistics about your entire topic database:

- **Topics by Agency** — Horizontal bar chart showing how many topics each agency posted
- **Topics by Component/Branch** — Breakdown by military branch or federal component
- **Topic Volume Over Time** — Line chart showing trends by agency across years
- **Top Capability Keywords** — Most frequent technical terms from topic titles and descriptions
- **Phase Distribution** — Donut chart of Phase I vs Phase II vs Phase III topics
- **Nominated & Passed by Agency** — Which agencies you're most actively pursuing or passing on
- **Topics by Source** — Breakdown by ingestion source

### Google Drive Integration

CaptureIQ can optionally sync project artifacts to your Google Drive.

**Setup:**

1. Go to **Settings → Google Drive** in the sidebar.
2. Follow the on-screen instructions to connect your Google account.
3. You will need a `credentials.json` file from the Google Cloud Console (OAuth 2.0 desktop app credentials).
4. Once connected, project artifacts can be uploaded to or linked from Drive folders.

> Google Drive credentials are stored locally in your CaptureIQ data directory and are never transmitted elsewhere.

---

## Data Storage

All CaptureIQ data is stored locally on your computer.

| Platform | Data Location |
|---|---|
| Mac | `~/CaptureIQ/` |
| Windows | `C:\Users\<you>\CaptureIQ\` |

This folder contains:

- `captureiq.db` — SQLite database (all topics, users, projects, preferences)
- `project_uploads/` — Uploaded proposal artifacts
- `gdrive_token.json` — Google Drive auth token (if connected)

> **Back this folder up regularly** to protect your data. The `captureiq.db` file is your entire pipeline.

---

## Distribution

### Mac — Apple Silicon (M1–M4)

1. Download `CaptureIQ-mac.zip` from the [Releases](https://github.com/ntoscano01/capture-iq/releases) page.
2. Unzip the file — you will find `CaptureIQ.app`.
3. Move `CaptureIQ.app` to your **Applications** folder.
4. Double-click to launch.

**Gatekeeper Warning:** On first launch, macOS may show a warning that the app is from an unidentified developer.

- Right-click (or Control-click) `CaptureIQ.app` → **Open** → Click **Open** in the dialog.
- You only need to do this once.

Alternatively, go to **System Settings → Privacy & Security** and click **Open Anyway** after attempting to launch.

### Mac — Intel

Apple Silicon builds will not run on Intel Macs. Intel users must build locally:

1. Clone this repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. If using Anaconda and you see a `pathlib` error:
   ```bash
   conda remove pathlib
   ```

3. Run the build script from the `sbir-pipeline/` directory:
   ```bash
   bash build_mac.sh
   ```

4. The finished app will be at `dist/CaptureIQ.app`. Move it to Applications.

### Windows

1. Download `CaptureIQ-windows.zip` from the [Releases](https://github.com/ntoscano01/capture-iq/releases) page.
2. Unzip to a folder of your choice (e.g., `C:\Program Files\CaptureIQ\`).
3. Double-click `CaptureIQ.exe` to launch.

**SmartScreen Warning:** Windows may warn that the app is from an unknown publisher.

- Click **More info** → **Run anyway**.

---

## Troubleshooting

### The app won't open / browser doesn't launch

Try opening your browser manually and navigating to `http://127.0.0.1:5000`.

### "Address already in use" / Port 5000 conflict

Another process is using port 5000. On macOS, the AirPlay Receiver uses this port by default.

**Mac:** Go to **System Settings → General → AirDrop & Handoff** and turn off **AirPlay Receiver**.

Or find and stop the conflicting process:
```bash
lsof -i :5000
kill <PID>
```

### "This application is not supported on this Mac"

You downloaded an Apple Silicon build but are running an Intel Mac. Build locally using the steps in [Mac — Intel](#mac--intel).

### Login page loops or shows "unauthorized"

Clear your browser cookies for `127.0.0.1` and try again.

### Topics show 0 after ingest

Try running ingestion again. Check your internet connection. If the issue persists, check the terminal/console for error messages.

### Google Drive won't connect

Ensure your `credentials.json` is a valid **OAuth 2.0 Desktop App** credential from Google Cloud Console with the Drive API enabled. Reinstall from **Settings → Google Drive**.

### Shutting down CaptureIQ

Use the **Quit CaptureIQ** button at the bottom of the sidebar. This cleanly shuts down the server. You can then close the browser tab.

---

## Building from Source

### Mac

```bash
cd sbir-pipeline
pip install pyinstaller
bash build_mac.sh
```

Output: `dist/CaptureIQ.app`

### Windows

```bat
cd sbir-pipeline
pip install pyinstaller
build_windows.bat
```

Output: `dist\CaptureIQ\CaptureIQ.exe`

### GitHub Actions (CI/CD)

Automated builds run on every push to `main` and on version tags (`v*`). Builds are available as GitHub Actions artifacts, and tagged releases are published to the Releases page automatically.

---

## License

This project is for internal use. Contact the repository owner for licensing questions.

---

*Built with Flask · Bootstrap 5 · Chart.js · SQLite · PyInstaller*
