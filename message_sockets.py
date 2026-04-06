from firebase_admin import auth
from flask_socketio import disconnect, join_room, emit
from flask import request, session
from sqlalchemy import or_, and_

from models import ClientCoaches, Users, Messages

from app import db, socketio


def verify_firebase_token(token):
    if token is None:
        disconnect()
        return None
    try:
        decoded_token = auth.verify_id_token(token)
        user = db.session.query(Users).filter(Users.firebase_user_id == decoded_token.get('user_id')).first()
        return user
    except Exception as e:
        print(e)
        disconnect()
        return None

def get_coaching_relationship(uid1, uid2):
    return db.session.query(ClientCoaches).filter(
        or_(
            and_(ClientCoaches.client_id == uid1, ClientCoaches.coach_id == uid2),
            and_(ClientCoaches.client_id == uid2, ClientCoaches.coach_id == uid1)
        )
    ).first()

def get_room():
    room = session.get('room')
    if not room:
        disconnect()
        return None
    return room


@socketio.on('connect')
def on_connect():
    user = verify_firebase_token(request.args.get('token'))
    if user is None:
        raise ConnectionRefusedError('User not found')

    session['user_id'] = user.user_id
    query = db.session.query(Users).filter(Users.user_id == user.user_id).first()
    session[str(user.user_id)] = query.first_name + ' ' + query.last_name


@socketio.on('join')
def on_join(data):
    user_id = session.get('user_id')
    other_id = data.get('other_id')
    session['other_id'] = other_id

    if not other_id:
        disconnect()
        return None

    relationship = get_coaching_relationship(user_id, other_id)
    if not relationship:
        disconnect()
        return None

    room = f'chat_{min(relationship.client_id, relationship.coach_id)}_{max(relationship.client_id, relationship.coach_id)}'
    session['room'] = room

    join_room(room)
    emit(
        'status', {'msg': 'User has joined the room.'},
        to=room
    )

@socketio.on('send_message')
def on_message(data):
    room = get_room()
    if not room:
        return

    emit(
        'new_message', {
            'sender_id': str(session.get('user_id')),
            'sender_name': session.get(str(session.get('user_id'))),
            'message': data.get('message')
        },
        to=room
    )

    new_message = Messages()
    new_message.message_sender = session.get('user_id')
    new_message.message_recipient = session.get('other_id')
    new_message.message_body = data.get('message')
    db.session.add(new_message)
    db.session.commit()