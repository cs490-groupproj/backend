import uuid
from unittest.mock import patch

from sqlalchemy import event

from models import ClientGoals, CoachSurveys, Users
from util import create_user, get_as, patch_as, post_as, post_as_uid


@event.listens_for(Users, 'before_insert')
def _assign_user_id_before_insert(mapper, connection, target):
    # SQLite test DB does not honor SQL Server's newid() default.
    if target.user_id is None:
        target.user_id = uuid.uuid4()


def test_users_register_endpoint(client, session):
    response = post_as_uid(
        client,
        'register-user',
        '/users/register',
        {
            'first_name': 'Register',
            'last_name': 'User',
            'email': 'register.user@email.com',
        },
    )

    body = response.get_json()
    assert response.status_code == 201
    assert body['first_name'] == 'Register'
    assert body['last_name'] == 'User'
    assert body['email'] == 'register.user@email.com'
    assert body['is_client'] is True
    assert body['is_coach'] is False
    assert body['is_active'] is True


def test_users_me_endpoint(client, session):
    user = create_user(session, 'me-user', is_admin=True)
    session.commit()

    response = get_as(client, user, '/users/me')
    body = response.get_json()

    assert response.status_code == 200
    assert body['user_id'] == str(user.user_id)
    assert body['is_client'] is True
    assert body['is_admin'] is True


def test_users_submit_coach_survey_endpoint(client, session):
    user = create_user(session, 'submit-survey-user')
    session.commit()

    response = post_as(
        client,
        user,
        '/users/onboarding/submit_coach_survey',
        {
            'specialization': 'Strength',
            'qualifications': 'NASM CPT',
            'coach_cost': 120,
        },
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body['user_id'] == str(user.user_id)
    assert body['specialization'] == 'Strength'
    assert body['qualifications'] == 'NASM CPT'
    assert body['coach_cost'] == 120


def test_users_patch_coach_survey_endpoint(client, session):
    user = create_user(session, 'patch-survey-user')
    survey = CoachSurveys()
    survey.user_id = user.user_id
    survey.specialization = 'General'
    survey.qualifications = 'Initial cert'
    session.add(survey)
    session.commit()

    response = patch_as(
        client,
        user,
        '/users/onboarding/coach_survey',
        {
            'specialization': 'Powerlifting',
            'qualifications': 'USAPL cert',
            'coach_cost': 150,
        },
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body['coach_survey_id'] == survey.coach_survey_id
    assert body['specialization'] == 'Powerlifting'
    assert body['qualifications'] == 'USAPL cert'
    assert body['coach_cost'] == 150


def test_users_profile_endpoint(client, session):
    user = create_user(session, 'profile-user', is_coach=True, is_client=True)

    survey = CoachSurveys()
    survey.user_id = user.user_id
    survey.specialization = 'Hypertrophy'
    survey.qualifications = 'CSCS'
    session.add(survey)

    goals = ClientGoals()
    goals.user_id = user.user_id
    goals.primary_goals = '110000'
    goals.weight_goal = 180
    goals.exercise_minutes_goal = 240
    goals.personal_goals = 'Stay consistent'
    session.add(goals)
    session.commit()

    response = get_as(client, user, f'/users/{user.user_id}/profile')
    body = response.get_json()

    assert response.status_code == 200
    assert body['user_id'] == str(user.user_id)
    assert body['coach_survey']['specialization'] == 'Hypertrophy'
    assert body['client_goals']['primary_goals_binary'] == '110000'


def test_users_edit_account_endpoint(client, session):
    user = create_user(session, 'edit-account-user')
    session.commit()

    with patch('endpoints.users.firebase_auth.update_user') as mock_update_user:
        response = patch_as(
            client,
            user,
            f'/users/{user.user_id}/edit_account',
            {
                'first_name': 'Edited',
                'last_name': 'Name',
                'email': 'edited.name@email.com',
            },
        )
        mock_update_user.assert_called_once_with(user.firebase_user_id, email='edited.name@email.com')

    body = response.get_json()
    assert response.status_code == 200
    assert body['first_name'] == 'Edited'
    assert body['last_name'] == 'Name'
    assert body['email'] == 'edited.name@email.com'


def test_users_delete_account_endpoint(client, session):
    user = create_user(session, 'delete-account-user')
    session.commit()

    with patch('endpoints.users.firebase_auth.delete_user') as mock_delete_user:
        response = post_as(
            client,
            user,
            f'/users/{user.user_id}/delete_account',
            {},
        )
        mock_delete_user.assert_called_once_with(user.firebase_user_id)

    body = response.get_json()
    assert response.status_code == 200
    assert body['user_id'] == str(user.user_id)
    assert body['is_active'] is False
