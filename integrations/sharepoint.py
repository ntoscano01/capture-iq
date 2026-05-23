"""
SharePoint Integration for CaptureIQ
Handles OAuth, file upload/download, and folder browsing via Microsoft Graph API
"""

import os
import json
import requests
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

# Configuration
SHAREPOINT_SCOPE = [
    "https://graph.microsoft.com/.default"
]

SHAREPOINT_TOKEN_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "sharepoint_token.json"
)


class SharePointConnector:
    """Handle SharePoint operations via Microsoft Graph API."""

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: Optional[str] = None):
        """Initialize connector with optional access token."""
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        } if access_token else {}

    @staticmethod
    def save_token(token_data: dict) -> bool:
        """Save token data to disk (encrypted in production)."""
        try:
            with open(SHAREPOINT_TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            return True
        except Exception as e:
            print(f"[SharePoint] Error saving token: {e}")
            return False

    @staticmethod
    def load_token() -> Optional[dict]:
        """Load saved token from disk."""
        try:
            if os.path.exists(SHAREPOINT_TOKEN_FILE):
                with open(SHAREPOINT_TOKEN_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[SharePoint] Error loading token: {e}")
        return None

    @staticmethod
    def has_token() -> bool:
        """Check if a stored token exists."""
        return os.path.exists(SHAREPOINT_TOKEN_FILE)

    def is_token_expired(self, token_data: dict) -> bool:
        """Check if token is expired."""
        if 'expires_at' not in token_data:
            return True
        return datetime.now().timestamp() > token_data['expires_at']

    def get_drive_items(self, site_id: str, folder_id: str = "root") -> List[Dict]:
        """List items in a SharePoint folder."""
        if not self.access_token:
            return []

        url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/items/{folder_id}/children"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            items = response.json().get('value', [])
            return [
                {
                    'id': item['id'],
                    'name': item['name'],
                    'type': 'folder' if 'folder' in item else 'file',
                    'size': item.get('size'),
                    'web_url': item.get('webUrl'),
                    'created_at': item.get('createdDateTime'),
                }
                for item in items
            ]
        except Exception as e:
            print(f"[SharePoint] Error listing items: {e}")
            return []

    def upload_file(self, site_id: str, folder_id: str, file_path: str,
                   file_name: Optional[str] = None) -> Optional[Dict]:
        """Upload a file to SharePoint."""
        if not self.access_token or not os.path.exists(file_path):
            return None

        file_name = file_name or os.path.basename(file_path)
        url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/items/{folder_id}:/{file_name}:/content"

        try:
            with open(file_path, 'rb') as f:
                response = requests.put(url, data=f, headers=self.headers, timeout=30)
                response.raise_for_status()
                item = response.json()
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'web_url': item.get('webUrl'),
                    'size': item.get('size'),
                }
        except Exception as e:
            print(f"[SharePoint] Error uploading file: {e}")
            return None

    def download_file(self, site_id: str, item_id: str) -> Optional[bytes]:
        """Download a file from SharePoint."""
        if not self.access_token:
            return None

        url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/items/{item_id}/content"

        try:
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[SharePoint] Error downloading file: {e}")
            return None

    def get_site_info(self) -> Optional[Dict]:
        """Get information about the connected site."""
        if not self.access_token:
            return None

        url = f"{self.GRAPH_API_ENDPOINT}/me"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            user = response.json()
            return {
                'user_principal_name': user.get('userPrincipalName'),
                'display_name': user.get('displayName'),
                'mail': user.get('mail'),
            }
        except Exception as e:
            print(f"[SharePoint] Error getting site info: {e}")
            return None

    def refresh_token(self, refresh_token: str, client_id: str, client_secret: str) -> Optional[Dict]:
        """Refresh an expired access token."""
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': 'https://graph.microsoft.com/.default'
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            token_data['expires_at'] = (
                datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            ).timestamp()
            return token_data
        except Exception as e:
            print(f"[SharePoint] Error refreshing token: {e}")
            return None


def is_connected() -> bool:
    """Check if SharePoint is connected."""
    token = SharePointConnector.load_token()
    return token is not None and 'access_token' in token


def get_auth_url(client_id: str, redirect_uri: str) -> str:
    """Generate OAuth authorization URL."""
    return (
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
        f"client_id={client_id}"
        "&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&scope=https://graph.microsoft.com/.default%20offline_access"
    )


def exchange_code_for_token(code: str, client_id: str, client_secret: str,
                           redirect_uri: str) -> Optional[Dict]:
    """Exchange authorization code for access token."""
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
        'scope': 'https://graph.microsoft.com/.default'
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        token_data['expires_at'] = (
            datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        ).timestamp()
        return token_data
    except Exception as e:
        print(f"[SharePoint] Error exchanging code: {e}")
        return None
