import json
import os
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Path to service account file
SERVICE_ACCOUNT_FILE = "config/serviceAccountKey.json"
PROJECT_ID = "jobs-academy"  # from your JSON (project_id)

# Scopes required for FCM
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

_credentials = None


def _get_credentials():
    """Lazily load the service account credentials on first use, instead of
    at import time, so the app can boot without config/serviceAccountKey.json
    present (push notification features just won't work until it's added)."""
    global _credentials
    if _credentials is None:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(
                f"{SERVICE_ACCOUNT_FILE} not found - FCM push notifications are not configured."
            )
        _credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    return _credentials


def get_access_token():
    """Generate an OAuth2 access token using the service account."""
    creds = _get_credentials()
    request = Request()
    creds.refresh(request)
    return creds.token

def send_fcm_message(device_token, title, body):
    """Send a push notification via FCM v1 API."""
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json; UTF-8",
    }

    payload = {
        "message": {
            "token": device_token,  # FCM device registration token from client
            "notification": {
                "title": title,
                "body": body,
            },
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()
