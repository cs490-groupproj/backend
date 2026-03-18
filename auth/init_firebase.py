import os
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    if not firebase_admin._apps: # prevent re-initialization

        base_dir = os.path.dirname(os.path.dirname(__file__))

        cred_path = os.path.join(base_dir, 'secrets', 'cs490-exercise-app-firebase-adminsdk.json')

        print('Initializing Firebase')

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)