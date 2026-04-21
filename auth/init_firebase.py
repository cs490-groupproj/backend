import base64
import json
import os
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    if not firebase_admin._apps: # prevent re-initialization

        cred_json = base64.b64decode(os.environ['FIREBASE_CREDENTIALS']).decode('utf-8')
        cred_dict = json.loads(cred_json)

        print('Initializing Firebase')

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)