from uuid import UUID


from models import *
from sqlalchemy import or_, and_
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g

message_blueprint = Blueprint('message_blueprint', __name__)

@message_blueprint.route('/unread_message_count')
@require_auth
def unread_messages():
    user_id = g.user.user_id
    messages = db.session.query(Messages).filter(Messages.message_recipient == user_id).filter(Messages.read.is_(False))

    return jsonify([{
        'unread_message_count': messages.count()
    }]), 200

@message_blueprint.route('/mark_received', methods=['POST'])
@require_auth
def mark_received():
    user_id = g.user.user_id
    other_party_user_id = request.args.get('other_party_user_id')

    other_party_user_id = UUID(other_party_user_id)

    db.session.query(Messages).filter(Messages.message_recipient == user_id).filter(Messages.message_sender == other_party_user_id)\
        .update({Messages.read: True}, synchronize_session=False)

    db.session.commit()

    return jsonify({
        'message': 'marked all as read'
    }), 200


@message_blueprint.route('/history')
@require_auth
def get_message_history():
    limit = request.args.get('limit')
    offset = request.args.get('offset')
    other_party_user_id = request.args.get('other_party_user_id')

    other_party_user_id = UUID(other_party_user_id)

    user_id = g.user.user_id

    if limit is None or offset is None or other_party_user_id is None:
        return jsonify({'error': 'limit and offset are required parameters'}), 400

    messages = db.session.query(Messages).filter(
        or_(
            and_(Messages.message_sender == user_id, Messages.message_recipient == other_party_user_id),
            and_(Messages.message_sender == other_party_user_id, Messages.message_recipient == user_id)
        )
    ).order_by(Messages.sent_date.desc()).limit(limit).offset(offset).all()

    return jsonify([{
        'message_sender': m.message_sender,
        'message_recipient': m.message_recipient,
        'message_body': m.message_body,
        'sent_date': m.sent_date,
        'read_by_recipient': m.read,
    } for m in messages]), 200