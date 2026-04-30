from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from util import create_user, post_as, get_as
from models import *

def _mock_firebase_user_metadata(last_sign_in_dt):
    user = MagicMock()
    user.user_metadata.last_sign_in_timestamp = int(last_sign_in_dt.timestamp() * 1000)
    return user

def test_active_users(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    now = datetime.now(timezone.utc)

    users = [
        _mock_firebase_user_metadata(now - timedelta(hours=12)),
        _mock_firebase_user_metadata(now - timedelta(days=3)),
        _mock_firebase_user_metadata(now - timedelta(days=20)),
        _mock_firebase_user_metadata(now - timedelta(days=40)),
    ]

    page = MagicMock()
    page.users = users
    page.get_next_page.return_value = None

    with patch('endpoints.admin.auth.list_users', return_value=page):

        response = get_as(client, admin, '/admin/users/active')

        data = response.get_json()

        assert data == {
            'dau': 1,
            'wau': 2,
            'mau': 3
        }

def test_active_users_unauth(client, session):
    user = create_user(session, 'other-user')

    response = get_as(client, user, '/admin/users/active')
    code = response.status_code
    assert code == 401

def test_get_all_users(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    users = [
        create_user(session, 'user1'),
        create_user(session, 'user2'),
        create_user(session, 'user3'),
    ]

    response = get_as(client, admin, '/admin/users/all?limit=2&offset=0')

    assert response.status_code == 200
    data = response.get_json()

    assert data['total_count'] >= 3

    assert len(data['users']) == 2

    for u in data['users']:
        assert 'user_id' in u
        assert 'first_name' in u
        assert 'last_name' in u
        assert 'is_active' in u

def test_get_all_users_unauth(client, session):
    user = create_user(session, 'other-user')

    response = get_as(client, user, '/admin/users/all?limit=10&offset=0')
    code = response.status_code
    assert code == 401

def test_ban_user(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    user = create_user(session, 'user1')

    payload = {'user_id': user.user_id }

    with patch('endpoints.admin.auth.update_user') as mock_update, patch('endpoints.admin.auth.revoke_refresh_tokens') as mock_revoke:
        response = post_as(client, admin, '/admin/users/ban', payload)

        assert response.status_code == 200
        assert user.is_active == False
        mock_update.assert_called_once()
        mock_revoke.assert_called_once()

def test_ban_user_unauth(client, session):
    false_admin = create_user(session, 'false-admin-user')
    user = create_user(session, 'other-user')

    payload = {'user_id': user.user_id }

    response = post_as(client, false_admin, '/admin/users/ban', payload)

    assert response.status_code == 401

def test_ban_user_missing_id(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    response = post_as(client, admin, '/admin/users/ban', {})
    assert response.status_code == 400
    assert response.get_json()['message'] == 'user_id missing in request body'

def test_ban_user_invalid_id(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    payload = {'user_id': 'bad-data'}

    response = post_as(client, admin, '/admin/users/ban', payload)

    assert response.status_code == 400
    assert response.get_json()['message'] == 'Invalid user ID'

def test_ban_user_firebase_down(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    user = create_user(session, 'user1')

    payload = {'user_id': user.user_id}

    with patch('endpoints.admin.auth.update_user', side_effect=Exception('Firebase Down')):
        response = post_as(client, admin, '/admin/users/ban', payload)

    assert response.status_code == 502
    assert user.is_active is False

def test_admin_get_coach_reports(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    coach = create_user(session, 'coach-user', is_coach=True)

    r1 = CoachReports()
    r1.coach_id = coach.user_id
    r1.report_body = 'Bad Behavior'

    r2 = CoachReports()
    r2.coach_id = coach.user_id
    r2.report_body = 'Spamming'

    session.add_all([r1, r2])
    session.commit()

    response = get_as(client, admin, '/admin/reports?limit=10&offset=0')

    assert response.status_code == 200
    data = response.get_json()

    assert data['total_count'] == 2
    assert len(data['reports']) == 2

    for report in data['reports']:
        assert 'coach_report_id' in report
        assert 'coach' in report
        assert 'report_message' in report

def test_admin_get_coach_reports_unauth(client, session):
    false_admin = create_user(session, 'false-admin-user')
    response = get_as(client, false_admin, '/admin/reports?limit=10&offset=0')

    assert response.status_code == 401

def test_admin_get_coach_reports_missing(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    response = get_as(client, admin, '/admin/reports')

    assert response.status_code == 400
    assert 'required' in response.get_json()['message']

def test_admin_reject_report(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    coach = create_user(session, 'coach-user', is_coach=True)

    report = CoachReports()
    report.coach_id = coach.user_id
    report.report_body = 'Spam'
    session.add(report)
    session.commit()

    payload = {'coach_report_id': report.coach_report_id }
    response = post_as(client, admin, '/admin/reject_report', payload)

    assert response.status_code == 200
    assert response.get_json()['message'] == 'Rejected report'

    deleted = session.query(CoachReports).filter(CoachReports.coach_report_id == report.coach_report_id).first()

    assert deleted is None

def test_admin_reject_report_unauth(client, session):
    false_admin = create_user(session, 'false-admin-user')

    payload = {'coach_report_id': 1}
    response = post_as(client, false_admin, '/admin/reject_report', payload)

    assert response.status_code == 401

def test_admin_reject_report_missing(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    response = post_as(client, admin, '/admin/reject_report', {})

    assert response.status_code == 400

def test_admin_reject_report_notfound(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    payload = {'coach_report_id': 99999}
    response = post_as(client, admin, '/admin/reject_report', payload)

    assert response.status_code == 404
    assert 'not found' in response.get_json()['message']

def test_admin_review_survey(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    u1 = create_user(session, 'user1')
    u2 = create_user(session, 'user2')
    coach = create_user(session, 'coach-user', is_coach=True)

    s1 = CoachSurveys()
    s1.user_id = u1.user_id
    s1.specialization = 'FITNESS'
    s1.qualifications = 'Olympian'

    s2 = CoachSurveys()
    s2.user_id = u2.user_id
    s2.specialization = 'NUTRITION'
    s2.qualifications = 'Nutritionist'

    s3 = CoachSurveys()
    s3.user_id = coach.user_id
    s3.specialization = 'BOTH'
    s3.qualifications = 'Expert'

    session.add_all([s1, s2, s3])
    session.commit()

    response = get_as(client, admin, '/admin/review_surveys?limit=10&offset=0')

    assert response.status_code == 200
    data = response.get_json()

    assert data['total_count'] == 2
    assert len(data['candidates']) == 2

    for c in data['candidates']:
        assert 'survey_id' in c
        assert 'user_id' in c
        assert 'first_name' in c
        assert 'last_name' in c
        assert 'email' in c
        assert 'specialization' in c
        assert 'qualifications' in c
        assert 'date_submitted' in c

def test_admin_review_survey_unauth(client, session):
    false_admin = create_user(session, 'admin-user')

    response = get_as(client, false_admin, '/admin/review_surveys?limit=10&offset=0')

    assert response.status_code == 401

def test_admin_review_survey_missing(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    response = get_as(client, admin, '/admin/review_surveys')

    assert response.status_code == 400
    assert 'required' in response.get_json()['message']

def test_admin_make_coach(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    user = create_user(session, 'user', is_coach=False)

    payload = { 'user_id': user.user_id }

    response = post_as(client, admin, '/admin/make_coach', payload)

    assert response.status_code == 200
    assert 'coaches' in response.get_json()['message']

    updated_user = db.session.query(Users).filter(Users.user_id == user.user_id).first()
    assert updated_user.is_coach == True

def test_admin_make_coach_unauth(client, session):
    admin = create_user(session, 'admin-user')
    user = create_user(session, 'user', is_coach=False)

    payload = { 'user_id': user.user_id }
    response = post_as(client, admin, '/admin/make_coach', payload)

    assert response.status_code == 401

def test_admin_make_coach_invalid(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    payload = { 'user_id': 'string' }
    response = post_as(client, admin, '/admin/make_coach', payload)

    assert response.status_code == 400
    assert 'Invalid' in response.get_json()['message']

def test_admin_reject_coach(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)
    coach = create_user(session, 'coach-user', is_coach=True)

    survey = CoachSurveys()
    survey.user_id = coach.user_id
    survey.specialization = 'BOTH'
    survey.qualifications = 'Professional'
    session.add(survey)
    session.commit()

    payload = { 'survey_id': survey.coach_survey_id }
    response = post_as(client, admin, '/admin/reject_application', payload)

    assert response.status_code == 200
    assert 'rejected' in response.get_json()['message']

    coach_survey = session.query(CoachSurveys).filter(CoachSurveys.coach_survey_id == survey.coach_survey_id).first()
    assert coach_survey is None

def test_admin_reject_coach_unauth(client, session):
    false_admin = create_user(session, 'admin-user')

    response = post_as(client, false_admin, '/admin/reject_application', {})

    assert response.status_code == 401

def test_admin_reject_coach_invalid(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    response = post_as(client, admin, '/admin/reject_application', {})

    assert response.status_code == 400
    assert 'missing' in response.get_json()['message']

def test_admin_reject_coach_notfound(client, session):
    admin = create_user(session, 'admin-user', is_admin=True)

    payload = {'survey_id': 99999}
    response = post_as(client, admin, '/admin/reject_application', payload)

    assert response.status_code == 404
    assert 'not found' in response.get_json()['message']