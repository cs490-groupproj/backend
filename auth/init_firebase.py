import os
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    if not firebase_admin._apps: # prevent re-initialization

        cred_dict = {
            'type': 'service_account',
            'project_id': os.environ['FIREBASE_PROJECT_ID'],
            'private_key_id': os.environ['FIREBASE_PRIVATE_KEY_ID'],
            'private_key': os.environ['FIREBASE_PRIVATE_KEY'].replace('\\n', '\n'),
            'client_email': os.environ['FIREBASE_CLIENT_EMAIL'],
            'client_id': os.environ['FIREBASE_CLIENT_ID'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': os.environ['FIREBASE_CLIENT_X509_CERT_URL'],
            'universe_domain': 'googleapis.com'
        }

        print('Initializing Firebase')

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)