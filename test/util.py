import uuid
from models import *
from unittest.mock import patch

def create_user(session, firebase_user_id, is_coach=False, is_client=True, is_admin=False):
    user = Users()
    user.user_id = uuid.uuid4()
    user.firebase_user_id = firebase_user_id
    user.first_name = firebase_user_id
    user.last_name = 'User'
    user.email = f'{firebase_user_id}@email.com'
    user.is_active = True
    user.is_coach = is_coach
    user.is_client = is_client
    user.is_admin = is_admin
    session.add(user)
    session.flush()
    return user


def post_as(client, user, path, payload):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.post(path, json=payload, headers={'Authorization': 'Bearer token'})


def post_as_uid(client, uid, path, payload):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': uid, 'email': f'{uid}@email.com'}
        return client.post(
            path,
            json=payload,
            headers={'Authorization': 'Bearer token', 'X-Test-Uid': uid},
        )


def get_as(client, user, path):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.get(path, headers={'Authorization': 'Bearer token'})


def delete_as(client, user, path):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.delete(path, headers={'Authorization': 'Bearer token'})


def patch_as(client, user, path, payload):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.patch(path, json=payload, headers={'Authorization': 'Bearer token'})


def put_as(client, user, path, payload):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.put(path, json=payload, headers={'Authorization': 'Bearer token'})