from uuid import UUID

from flask import Blueprint, g, jsonify, request
from firebase_admin import auth
from datetime import datetime, timezone, timedelta

from auth.authentication import require_auth
from auth.util import can_access_admin_endpoint
from models import *

admin_blueprint = Blueprint('admin', __name__)

@admin_blueprint.route('/users/active')
@require_auth
def active_users():
    """
    Get active user counts
    ---
    tags:
        - Admin
    responses:
        200:
            description: Active user counts
            schema:
                type: object
                properties:
                    dau:
                        type: integer
                    wau:
                        type: integer
                    mau:
                        type: integer
    """

    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    now = datetime.now(timezone.utc)
    cutoffs = {
        'dau': now - timedelta(days=1),
        'wau': now - timedelta(weeks=1),
        'mau': now - timedelta(days=30),
    }
    counts = {'dau': 0, 'wau': 0, 'mau': 0}

    page = auth.list_users()
    while page:
        for user in page.users:
            last_sign_in = user.user_metadata.last_sign_in_timestamp
            if not last_sign_in:
                continue
            last_sign_in_dt = datetime.fromtimestamp(
                last_sign_in / 1000, tz=timezone.utc
            )
            for key, cutoff in cutoffs.items():
                if last_sign_in_dt >= cutoff:
                    counts[key] += 1

        page = page.get_next_page()

    return jsonify(counts), 200

@admin_blueprint.route('/users/all')
@require_auth
def all_users():
    """
    Get all users
    ---
    tags:
        - Admin
    paramters:
        - name: limit
          in: path
          required: true
          type: integer
        - name: offset
          in: path
          required: true
          type: integer
    responses:
        200:
            description: All users
            schema:
                type: object
                properties:
                    total_count:
                        type: integer
                    users:
                        type: array
                        items:
                            type: object
                            properties:
                                user_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
    """
    limit = request.args.get('limit')
    offset = request.args.get('offset')

    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    query = db.session.query(Users)

    total = query.count()

    users = query.limit(limit).offset(offset).all()

    return jsonify({
        'total_count': total,
        'users': [{
            'user_id': u.user_id,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
        } for u in users]
    }), 200

@admin_blueprint.route('/users/ban', methods=['POST'])
@require_auth
def ban_user():
    """
    Ban a user
    ---
    tags:
        - Admin
    paramters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                user_id:
                    type: string
    responses:
        200:
            description: Ban user
            schema:
                type: object
                properties:
                    message:
                        type: string
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401


    user_id = request.json.get('user_id')

    if user_id is None:
        return jsonify({'message': 'user_id missing in request body'}), 400

    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'message': 'Invalid user ID'}), 400

    user = db.session.query(Users).filter(Users.user_id == user_id).first()

    user.is_active = False

    return jsonify({
        'message': 'User banned'
    }), 200

