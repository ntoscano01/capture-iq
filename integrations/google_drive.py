"""
CaptureIQ — Google Drive Integration
Handles OAuth2 auth flow and file operations against the Drive API.

Setup (one-time):
  1. Go to https://console.cloud.google.com/
  2. Create a project → Enable the Google Drive API
  3. APIs & Services → Credentials → Create OAuth 2.0 Client ID
     - Application type: Web application
     - Authorised redirect URI: http://127.0.0.1:5000/settings/gdrive/callback
  4. Download JSON → rename to credentials.json → place next to app.py
  5. In the app, go to Settings → Google Drive → Connect
"""

import io
import os

BASE_DIR   = os.path.dirname(os.path.dirname(__file__))   # sbir-pipeline/
TOKEN_PATH = os.path.join(BASE_DIR, "gdrive_token.json")
CREDS_PATH = os.path.join(BASE_DIR, "credentials.json")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT_FOLDER_NAME = "CaptureIQ"


# ── Auth helpers ───────────────────────────────────────────────────────────────

def has_credentials_file() -> bool:
    return os.path.exists(CREDS_PATH)


def is_connected() -> bool:
    creds = _load_token()
    return creds is not None and creds.valid


def _load_token():
    """Load and auto-refresh stored token. Returns None if unavailable."""
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        return creds if creds.valid else None
    except Exception:
        return None


def _save_token(creds):
    with open(TOKEN_PATH, "w") as fh:
        fh.write(creds.to_json())


def get_auth_url(redirect_uri: str) -> str:
    """Return the Google OAuth2 authorisation URL."""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(CREDS_PATH, scopes=SCOPES,
                                         redirect_uri=redirect_uri)
    url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return url


def exchange_code(code: str, redirect_uri: str):
    """Exchange the OAuth2 code for a token and persist it."""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(CREDS_PATH, scopes=SCOPES,
                                         redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    _save_token(flow.credentials)


def revoke():
    """Disconnect — delete the stored token."""
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)


# ── Drive service ──────────────────────────────────────────────────────────────

def _service():
    from googleapiclient.discovery import build
    creds = _load_token()
    if not creds:
        raise RuntimeError("Google Drive is not connected.")
    return build("drive", "v3", credentials=creds)


# ── Folder management ──────────────────────────────────────────────────────────

def get_or_create_root_folder() -> str:
    """Return the ID of the CaptureIQ root folder in Drive (creates if absent)."""
    svc = _service()
    q = (f"name='{ROOT_FOLDER_NAME}' "
         f"and mimeType='application/vnd.google-apps.folder' "
         f"and trashed=false")
    res = svc.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": ROOT_FOLDER_NAME,
            "mimeType": "application/vnd.google-apps.folder"}
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]


def get_or_create_project_folder(project_name: str, project_id: int) -> str:
    """Return the Drive folder ID for a project (creates if absent)."""
    svc = _service()
    root_id = get_or_create_root_folder()
    # Sanitise name for Drive
    safe_name = f"{project_name[:80]} (CIQ-{project_id})"
    q = (f"name='{safe_name}' "
         f"and mimeType='application/vnd.google-apps.folder' "
         f"and '{root_id}' in parents "
         f"and trashed=false")
    res = svc.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": safe_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [root_id]}
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]


# ── File operations ────────────────────────────────────────────────────────────

def upload_file(folder_id: str, local_path: str,
                filename: str, mime_type: str = None) -> tuple[str, str]:
    """Upload a local file to Drive. Returns (gdrive_file_id, web_view_link)."""
    from googleapiclient.http import MediaFileUpload
    svc = _service()
    mime_type = mime_type or "application/octet-stream"
    meta = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    f = svc.files().create(body=meta, media_body=media,
                           fields="id,webViewLink").execute()
    return f["id"], f.get("webViewLink", "")


def download_file(gdrive_file_id: str) -> io.BytesIO:
    """Download a Drive file. Returns a BytesIO buffer."""
    from googleapiclient.http import MediaIoBaseDownload
    svc = _service()
    req = svc.files().get_media(fileId=gdrive_file_id)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    return buf


def delete_file(gdrive_file_id: str):
    """Permanently delete a file from Drive."""
    _service().files().delete(fileId=gdrive_file_id).execute()


def get_file_info(gdrive_file_id: str) -> dict:
    """Return name, size, and webViewLink for a Drive file."""
    return _service().files().get(
        fileId=gdrive_file_id,
        fields="id,name,size,webViewLink"
    ).execute()
