from uuid import UUID

from flask import Blueprint, g, jsonify, request
from sqlalchemy import and_, func, or_

from auth.authentication import require_auth
from models import *

message_blueprint = Blueprint("message_blueprint", __name__)


@message_blueprint.route("/unread_message_count")
@require_auth
def unread_messages():
    """
    Get unread message count
    ---
    tags:
        - Messages
    responses:
        200:
            description: Get unread message counts by conversation
            schema:
                type: object
                properties:
                    unread_message_counts:
                        type: array
                        items:
                            type: object
                            properties:
                                message_sender_id:
                                    type: string
                                message_sender_name:
                                    type: string
                                unread_count:
                                    type: integer
    """
    user_id = g.user.user_id
    messages = (
        db.session.query(
            Messages.message_sender,
            Users.first_name,
            Users.last_name,
            func.count(Messages.message_id),
        )
        .join(Users, Messages.message_sender == Users.user_id)
        .filter(Messages.message_recipient == user_id)
        .filter(Messages.read == False)
        .group_by(Messages.message_sender, Users.first_name, Users.last_name)
        .all()
    )

    return jsonify(
        {
            "unread_message_counts": [
                {
                    "message_sender_id": m[0],
                    "message_sender_name": (m[1] + " " + m[2]),
                    "unread_count": m[3],
                }
                for m in messages
            ]
        }
    ), 200


@message_blueprint.route("/mark_received", methods=["POST"])
@require_auth
def mark_received():
    """
        Mark messages as received
        ---
        tags:
            - Messages
        parameters:
            - name: other_party_user_id
              in: path
              required: true
              type: string
        responses:
            200:
                description: Marked all messages as read
                schema:
                    type: object
                    properties:
                        message:
                            type: string
        """
    user_id = g.user.user_id
    other_party_user_id = request.json.get("other_party_user_id")

    other_party_user_id = UUID(other_party_user_id)

    db.session.query(Messages).filter(
        Messages.message_recipient == user_id
    ).filter(Messages.message_sender == other_party_user_id).update(
        {Messages.read: True}, synchronize_session=False
    )

    db.session.commit()

    return jsonify({"message": "marked all as read"}), 200


@message_blueprint.route("/history")
@require_auth
def get_message_history():
    """
        Get message history
        ---
        tags:
            - Messages
        parameters:
            - name: limit
              in: path
              required: true
              type: integer
            - name: offset
              in: path
              required: true
              type: integer
            - name: other_party_user_id
              in: path
              required: true
              type: string
        responses:
            200:
                description: Get a user's message history, ordered by date descending
                schema:
                    type: object
                    properties:
                        messages:
                            type: array
                            items:
                                type: object
                                properties:
                                    message_sender:
                                        type: string
                                    message_recipient:
                                        type: string
                                    message_body:
                                        type: string
                                    sent_date:
                                        type: string
                                    read_by_recipient:
                                        type: boolean
            400:
                description: Error with parameters
        """
    limit = request.args.get("limit")
    offset = request.args.get("offset")
    other_party_user_id = request.args.get("other_party_user_id")

    other_party_user_id = UUID(other_party_user_id)

    user_id = g.user.user_id

    if limit is None or offset is None or other_party_user_id is None:
        return jsonify(
            {"error": "limit and offset are required parameters"}
        ), 400

    messages = (
        db.session.query(Messages)
        .filter(
            or_(
                and_(
                    Messages.message_sender == user_id,
                    Messages.message_recipient == other_party_user_id,
                ),
                and_(
                    Messages.message_sender == other_party_user_id,
                    Messages.message_recipient == user_id,
                ),
            )
        )
        .order_by(Messages.sent_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return jsonify(
        {
            "messages": [
                {
                    "message_sender": m.message_sender,
                    "message_recipient": m.message_recipient,
                    "message_body": m.message_body,
                    "sent_date": m.sent_date,
                    "read_by_recipient": m.read,
                }
                for m in messages
            ]
        }
    ), 200


@message_blueprint.route('/chatters', methods=['GET'])
@require_auth
def get_chatters():
    """
        Get all chat participants (clients + coaches) for the logged-in user
        ---
        tags:
            - Messages
        responses:
            200:
                description: List of users the current user can chat with
                schema:
                    type: object
                    properties:
                        chatters:
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
            401:
               description: Unauthorized
        """
    user = g.user

    def to_user(u):
        return {
            "user_id": u.user_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
        }

    chatters_map = {}

    if user.is_client:
        coaches = (
            db.session.query(Users)
            .join(ClientCoaches, ClientCoaches.coach_id == Users.user_id)
            .filter(ClientCoaches.client_id == user.user_id)
            .filter(Users.is_active == True)
            .all()
        )
        
        for coach in coaches:
            chatters_map[coach.user_id] = to_user(coach)
            
    if user.is_coach:
        clients = (
            db.session.query(Users)
            .join(ClientCoaches, ClientCoaches.client_id == Users.user_id)
            .filter(ClientCoaches.coach_id == user.user_id)
            .filter(Users.is_active == True)
            .all()
        )

        for client in clients:
            chatters_map[client.user_id] = to_user(client)

    chatters = list(chatters_map.values())
    chatters.sort(key=lambda user: (user["first_name"], user["last_name"]))
    return jsonify({"chatters": chatters}), 200