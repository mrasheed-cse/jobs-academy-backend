# notifications/firebase_client.py
import os
import firebase_admin
from firebase_admin import credentials

_cred_path = "config/serviceAccountKey.json"
if os.path.exists(_cred_path) and not firebase_admin._apps:
    cred = credentials.Certificate(_cred_path)
    firebase_admin.initialize_app(cred)
