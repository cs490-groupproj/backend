from functools import wraps
from flask import request, jsonify, g
from firebase_admin import auth

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
            g.user = decoded_token
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return f(*args, **kwargs)

    return decorator