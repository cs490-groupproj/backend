from datetime import datetime, timezone, timedelta
from util import create_user, post_as, get_as
from models import *

def _create_billing_object(user_id):
    billing = ClientBilling()
    billing.client_id = user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 5
    billing.card_exp_year = 30
    billing.card_security_number = 30
    billing.card_name = 'Credit Card'
    billing.card_address_1 = '123 Road St'
    billing.card_address_2 = None
    billing.card_city = 'Newark'
    billing.card_postcode = '07102'
    billing.renew_day_number = datetime.now().day

    return billing

def test_messages_unread(session, client):
    user_a = create_user(session, 'user-a')
    user_b = create_user(session, 'user-b')

    recipient = create_user(session, 'recipient')

    m1 = Messages()
    m1.message_sender = user_a.user_id
    m1.message_recipient = recipient.user_id
    m1.message_body = 'Test1'
    m1.read = False

    m2 = Messages()
    m2.message_sender = user_a.user_id
    m2.message_recipient = recipient.user_id
    m2.message_body = 'Test2'
    m2.read = False

    m3 = Messages()
    m3.message_sender = user_b.user_id
    m3.message_recipient = recipient.user_id
    m3.message_body = 'Test3'
    m3.read = False

    m4 = Messages()
    m4.message_sender = user_b.user_id
    m4.message_recipient = recipient.user_id
    m4.message_body = 'Test4'
    m4.read = True

    session.add_all([m1, m2, m3, m4])
    session.commit()

    response = get_as(client, recipient, 'messages/unread_message_count')

    assert response.status_code == 200

    data = response.get_json()['unread_message_counts']
    assert len(data) == 2

    results = {
        item['message_sender_id']: item for item in data
    }

    assert results[str(user_a.user_id)]['unread_count'] == 2
    assert results[str(user_b.user_id)]['unread_count'] == 1

    assert results[str(user_a.user_id)]['message_sender_name'] == 'user-a User'

def test_messages_read_none(client, session):
    recipient = create_user(session, 'recipient')

    response = get_as(client, recipient, 'messages/unread_message_count')

    assert response.status_code == 200
    assert response.get_json()['unread_message_counts'] == []

def test_messages_mark_received(client, session):
    user = create_user(session, 'recipient')
    other = create_user(session, 'sender')

    m1 = Messages()
    m1.message_sender = other.user_id
    m1.message_recipient = user.user_id
    m1.message_body = 'Test1'
    m1.read = False

    m2 = Messages()
    m2.message_sender = other.user_id
    m2.message_recipient = user.user_id
    m2.message_body = 'Test2'
    m2.read = False

    other_sender = create_user(session, 'other-sender')
    m3 = Messages()
    m3.message_sender = other_sender.user_id
    m3.message_recipient = user.user_id
    m3.message_body = 'Test3'
    m3.read = False

    session.add_all([m1, m2, m3])
    session.commit()

    payload = {
        'other_party_user_id': str(other.user_id),
    }

    response = post_as(client, user, 'messages/mark_received', payload)

    assert response.status_code == 200
    assert 'marked' in response.get_json()['message'] and 'read' in response.get_json()['message']

def test_messages_history(client, session):
    user = create_user(session, 'user-a')
    other = create_user(session, 'user-b')

    now = datetime.now(timezone.utc)

    m1 = Messages()
    m1.message_sender = user.user_id
    m1.message_recipient = other.user_id
    m1.message_body = 'Test1'
    m1.sent_date = now - timedelta(minutes=5)
    m1.read = False

    m2 = Messages()
    m2.message_sender = other.user_id
    m2.message_recipient = user.user_id
    m2.message_body = 'Test2'
    m2.sent_date = now - timedelta(minutes=2)
    m2.read = False

    session.add_all([m1, m2])
    session.commit()

    response = get_as(client, user, f'messages/history?limit=10&offset=0&other_party_user_id={other.user_id}')

    assert response.status_code == 200
    data = response.get_json()['messages']

    assert len(data) == 2
    assert data[0]['message_body'] == 'Test1' or 'Test2'
    assert data[1]['message_body'] == 'Test1' or 'Test2'

    assert {m['message_sender'] for m in data} == {
        str(user.user_id),
        str(other.user_id),
    }

def test_messages_history_missing(client, session):
    user = create_user(session, 'user-a')

    response = get_as(client, user, '/messages/history')

    assert response.status_code == 400
    assert 'required parameters' in response.get_json()['error']

def test_messages_history_invalid(client, session):
    user = create_user(session, 'user-a')

    response = get_as(client, user, '/messages/history?limit=10&offset=0&other_party_user_id=0')

    assert response.status_code == 400
    assert 'Invalid' in response.get_json()['message']

def test_messages_chatters_client(client, session):
    client_user = create_user(session, 'client')
    coach1 = create_user(session, 'coach1', is_coach=True)
    coach2 = create_user(session, 'coach2', is_coach=True)

    billing = _create_billing_object(client_user.user_id)
    session.add(billing)
    session.flush()

    r1 = ClientCoaches()
    r1.client_id = client_user.user_id
    r1.coach_id = coach1.user_id
    r1.client_billing_id = billing.client_billing_id

    r2 = ClientCoaches()
    r2.client_id = client_user.user_id
    r2.coach_id = coach2.user_id
    r2.client_billing_id = billing.client_billing_id

    session.add_all([r1, r2])
    session.commit()

    response = get_as(client, client_user, 'messages/chatters')

    assert response.status_code == 200
    data = response.get_json()

    assert len(data['chatters']) == 2

    ids = {c['user_id'] for c in data['chatters']}
    assert str(coach1.user_id) in ids
    assert str(coach2.user_id) in ids

def test_chatters_coach_view(client, session):
    coach = create_user(session, "coach1", is_coach=True)

    client1 = create_user(session, "clientA", is_client=True)
    client2 = create_user(session, "clientB", is_client=True)

    billing1 = _create_billing_object(client1.user_id)
    billing2 = _create_billing_object(client2.user_id)

    session.add_all([billing1, billing2])
    session.flush()

    r1 = ClientCoaches()
    r1.client_id = client1.user_id
    r1.coach_id = coach.user_id
    r1.client_billing_id = billing1.client_billing_id

    r2 = ClientCoaches()
    r2.client_id = client2.user_id
    r2.coach_id = coach.user_id
    r2.client_billing_id = billing2.client_billing_id

    session.add_all([r1, r2])
    session.commit()

    response = get_as(client, coach, "/messages/chatters")
    assert response.status_code == 200

    data = response.get_json()

    assert len(data['chatters']) == 2

    ids = {c["user_id"] for c in data['chatters']}
    assert str(client1.user_id) in ids
    assert str(client2.user_id) in ids