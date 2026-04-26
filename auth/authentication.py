from functools import wraps
from uuid import UUID

from flask import request, jsonify, g
from firebase_admin import auth

from models import db, Users, ClientCoaches

def require_auth(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)

        if not auth_header:
            return jsonify({'error': 'Missing Authorization Header'}), 401

        try:
            # Expect format "Bearer {token}"
            token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({'error': 'Invalid Authorization Header'}), 401

        try:
            decoded_token = auth.verify_id_token(token)
            print(decoded_token)
            g.firebase_user = decoded_token

        except Exception as e:
            return jsonify({'error': 'Invalid or expired token'}), 401

        firebase_uid = decoded_token.get('uid') or decoded_token.get('user_id') or decoded_token.get('sub')

        if request.path != '/users/register':
            g.user = (
                db.session.query(Users)
                .filter(Users.firebase_user_id == firebase_uid)
                .first()
            )
            if g.user is None:
                return jsonify({'error': 'This user has an account, but has not yet registered.', 'hint': 'If you are a frontend developer, call POST /users/register.'}), 400

            # Check if user_id is set
            if g.user.user_id is None:
                return jsonify({'error': 'User account is incomplete. Please contact support.'}), 500

            # Gets the clients that the authenticated user coaches
            g.clients = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == g.user.user_id).all()
            g.clients_ids = [c.client_id for c in g.clients]

        return f(*args, **kwargs)

    return decorator