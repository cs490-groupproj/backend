from functools import wraps
from flask import request, jsonify, g
from firebase_admin import auth

from models import db, Users

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

        g.user = db.session.query(Users).where(Users.firebase_user_id == decoded_token.get('user_id')).first()
        if g.user is None:
            new_user = Users()
            new_user.firebase_user_id = decoded_token.get('user_id')
            new_user.first_name = 'New'
            new_user.last_name = 'User'
            new_user.email = decoded_token.get('email')
            new_user.is_coach = False
            new_user.is_active = True
            db.session.add(new_user)
            db.session.commit()
            g.user = db.session.query(Users).where(Users.firebase_user_id == decoded_token.get('user_id')).first()

        return f(*args, **kwargs)

    return decorator