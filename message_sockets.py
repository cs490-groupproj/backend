from uuid import UUID

from firebase_admin import auth
from flask import request, session
from flask_socketio import disconnect, emit, join_room, leave_room
from sqlalchemy import and_, or_

from app import db, socketio
from models import ClientCoaches, Messages, Users


def verify_firebase_token(token):
    if token is None:
        disconnect()
        print("disconnect no token")
        return None
    try:
        decoded_token = auth.verify_id_token(token)
        user = (
            db.session.query(Users)
            .filter(Users.firebase_user_id == decoded_token.get("user_id"))
            .first()
        )
        return user
    except Exception as e:
        print(e)
        disconnect()
        return None


def get_coaching_relationship(uid1, uid2):
    return (
        db.session.query(ClientCoaches)
        .filter(
            or_(
                and_(
                    ClientCoaches.client_id == uid1,
                    ClientCoaches.coach_id == uid2,
                ),
                and_(
                    ClientCoaches.client_id == uid2,
                    ClientCoaches.coach_id == uid1,
                ),
            )
        )
        .first()
    )


def get_room():
    room = session.get("room")
    if not room:
        disconnect()
        print("disconnect no room")
        return None
    return room


def is_user_online(user_id):
    return bool(connected_users.get(user_id))


def get_connected_users():
    return list(connected_users.keys())


connected_users = {}
in_chat_users = {}


@socketio.on("connect")
def on_connect():
    user = verify_firebase_token(request.args.get("token"))
    if user is None:
        raise ConnectionRefusedError("User not found")

    user_id = str(user.user_id)
    session["user_id"] = user_id

    # Create personal room for chat notifications
    join_room(f"user_{user_id}")

    sid = request.sid

    if user_id not in connected_users:
        connected_users[user_id] = set()

    connected_users[user_id].add(sid)

    query = (
        db.session.query(Users).filter(Users.user_id == user.user_id).first()
    )
    session[user_id] = query.first_name + " " + query.last_name


@socketio.on("join")
def on_join(data):
    user_id = session.get("user_id")

    try:
        other_id = str(UUID(data.get("other_id")))
        session["other_id"] = other_id

        # add the chat user joined to in chat users so read status can be correctly determined
        if not in_chat_users.get(user_id):
            in_chat_users[user_id] = set()
        in_chat_users[user_id].add(other_id)
    except (ValueError, AttributeError):
        disconnect()
        print("disconnect bad uuid")
        return

    relationship = get_coaching_relationship(user_id, other_id)
    if not relationship:
        disconnect()
        print("disconnect bad relationship")
        return None

    old_room = session.get("room")
    if old_room:
        leave_room(old_room)

    room = f"chat_{min(relationship.client_id, relationship.coach_id)}_{max(relationship.client_id, relationship.coach_id)}"
    session["room"] = room

    join_room(room)
    emit("status", {"msg": "User has joined the room."}, to=room)


# exists so read receipts can be correctly sent, with in_chat_users dict
@socketio.on("leave")
def on_leave(data):
    user_id = session.get("user_id")

    try:
        other_id = str(UUID(data.get("other_id")))

        # remove the chat user joined to in chat users so read status can be correctly determined
        if user_id in in_chat_users and other_id:
            in_chat_users[user_id].discard(other_id)
            if not in_chat_users[user_id]:
                del in_chat_users[user_id]
    except (ValueError, AttributeError):
        disconnect()
        print("disconnect bad uuid")
        return

    old_room = session.get("room")
    if old_room:
        leave_room(old_room)


@socketio.on("send_message")
def on_message(data):
    room = get_room()
    if not room:
        return

    sender = session.get("user_id")
    recipient = session.get("other_id")

    emit(
        "new_message",
        {
            "sender_id": sender,
            "sender_name": session.get(str(sender)),
            "message": data.get("message"),
        },
        to=room,
    )

    new_message = Messages()
    new_message.message_sender = sender
    new_message.message_recipient = recipient
    new_message.message_body = data.get("message")

    # update read status to true if recipient is in the chat with sender, otherwise false
    if sender in in_chat_users.get(recipient, set()):
        new_message.read = True
    else:
        new_message.read = False
        # Sends message to private user room for notifications
        emit(
            "notification",
            {
                "notification_type": "chat_message",
                "sender_id": sender,
                "sender_name": session.get(str(sender)),
            },
            to=f"user_{recipient}",
        )

    db.session.add(new_message)
    db.session.commit()


@socketio.on("disconnect")
def on_disconnect():
    user_id = session.get("user_id")
    other_id = session.get("other_id")

    sid = request.sid

    if not user_id:
        return

    if user_id in connected_users:
        connected_users[user_id].discard(sid)

        if not connected_users[user_id]:
            del connected_users[user_id]

    if user_id in in_chat_users and other_id:
        in_chat_users[user_id].discard(other_id)
        if not in_chat_users[user_id]:
            del in_chat_users[user_id]
