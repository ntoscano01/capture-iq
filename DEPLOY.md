# CaptureIQ — Deployment Guide
## Hosted PWA: Chrome, Safari, iOS, Android

This guide walks you through deploying CaptureIQ to Railway so it's accessible
from any browser or device — desktop, tablet, or phone.

---

## Part 1: Deploy to Railway (15–20 minutes)

### Step 1 — Create a Railway account
1. Go to **https://railway.app** and sign up (free tier available, paid from $5/month)
2. Connect your GitHub account when prompted

### Step 2 — Push the latest code to GitHub
From your terminal in the `sbir-pipeline/` directory:
```bash
git add .
git commit -m "feat: PWA support + Railway deployment config"
git push origin main
```

### Step 3 — Create a new Railway project
1. In Railway dashboard → **New Project**
2. Choose **Deploy from GitHub repo**
3. Select your `sbir-pipeline` repository
4. Railway auto-detects Python and runs `nixpacks` to build

### Step 4 — Add a Persistent Volume (critical — protects your database)
Railway containers reset on redeploy. You must mount a volume to persist the SQLite DB:

1. In your Railway service → **Volumes** tab → **Add Volume**
2. Set **Mount Path** to `/app/data`
3. Click **Save**

Then update `database.py` to use the volume path in production:

```python
# In database.py, change DB_PATH to:
DB_PATH = os.environ.get(
    "CAPTUREIQ_DB_PATH",
    os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")
)
```

And set the environment variable in Railway (Step 5).

### Step 5 — Set Environment Variables
In Railway → your service → **Variables** tab, add:

| Variable | Value | Notes |
|---|---|---|
| `CAPTUREIQ_ENV` | `production` | Enables HTTPS cookies, disables debug |
| `CAPTUREIQ_SECRET_KEY` | (random 32+ char string) | **Required** — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `CAPTUREIQ_DB_PATH` | `/app/data/captureiq.db` | Points to the persistent volume |
| `PORT` | (leave blank) | Railway sets this automatically |

### Step 6 — Deploy
Railway deploys automatically on every `git push`. Watch the **Deploy Logs** tab.

First deploy takes ~3 minutes. Subsequent deploys are faster.

### Step 7 — Get your URL
Railway provides a URL like `https://captureiq-production.up.railway.app`.

In Railway → Settings → **Domains**, you can:
- Use the auto-generated `.up.railway.app` domain (free, HTTPS included)
- Add a **custom domain** (e.g. `captureiq.yourcompany.com`) — HTTPS is automatic

---

## Part 2: Install as PWA on Devices

### Chrome (Desktop or Android)
1. Open your Railway URL in Chrome
2. Log in to CaptureIQ
3. Click the **install icon** (⊕) in the address bar, or open the Chrome menu → **Install CaptureIQ**
4. The app opens in its own window, appears in your taskbar/app drawer

### Safari on iPhone / iPad
1. Open your Railway URL in Safari
2. Tap the **Share** button (box with arrow up)
3. Scroll down and tap **Add to Home Screen**
4. Tap **Add** — the CaptureIQ icon appears on your home screen
5. Launch it from the home screen for full-screen app mode

### Android (Chrome)
1. Open your Railway URL in Chrome
2. Tap the **three-dot menu** → **Add to Home screen**
3. Or wait for the Chrome install banner to appear automatically
4. The app installs and appears in your app drawer

---

## Part 3: Custom Domain (Optional)

1. Buy a domain (e.g. `captureiq.io`) from Namecheap, Cloudflare, or similar
2. In Railway → Settings → Domains → **Add Custom Domain**
3. Enter your domain and follow the DNS instructions (CNAME record)
4. HTTPS is provisioned automatically via Let's Encrypt

---

## Part 4: Initial Setup After Deployment

1. Navigate to your app URL — you'll be redirected to `/setup`
2. Create your admin account
3. Go to **Admin → Settings** and configure:
   - Organization name
   - SMTP email settings (for password reset emails)
4. Create additional user accounts for your team

---

## Ongoing Operations

### Updating the app
```bash
# Make changes locally, test, then:
git add .
git commit -m "your change description"
git push origin main
# Railway auto-deploys in ~2 minutes
```

### Database backups
- Use **Admin → Database → Download Backup** in the app to download a `.db` file
- Store it in a safe location (Google Drive, S3, etc.)
- Recommended: download before every major update

### Monitoring
- Railway dashboard shows CPU, memory, and request logs
- Set up Railway's built-in alerts for downtime

---

## Troubleshooting

| Problem | Solution |
|---|---|
| App shows "Application Error" | Check Deploy Logs in Railway for Python errors |
| Database resets on redeploy | Confirm Volume is mounted at `/app/data` and `CAPTUREIQ_DB_PATH` is set |
| Login redirects to HTTP | Ensure `CAPTUREIQ_ENV=production` is set |
| PWA won't install on iPhone | Must be HTTPS — Railway handles this automatically |
| "Add to Home Screen" missing | Open in Safari (not Chrome) on iOS |
| Google Drive integration broken | OAuth must be reconfigured for the production URL |

---

## Architecture Overview

```
Browser / PWA
     │
     ▼ HTTPS
Railway (gunicorn + Flask)
     │
     ├── SQLite DB (persistent volume at /app/data/)
     ├── Static files (icons, CSS, JS, service worker)
     └── File uploads (project_uploads/ — also needs volume in production)
```

For larger teams (5+ concurrent users), consider migrating from SQLite to
PostgreSQL. Railway offers managed Postgres as an add-on.
