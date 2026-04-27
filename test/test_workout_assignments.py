import uuid
from datetime import time
from unittest.mock import patch

from models import (
    ClientBilling,
    ClientCoaches,
    Users,
    WorkoutPlanClientDays,
    WorkoutPlanClients,
    WorkoutPlanDays,
    WorkoutPlans,
)


def _create_user(session, firebase_user_id, is_coach=False, is_client=True, is_admin=False):
    user = Users()
    user.user_id = uuid.uuid4()
    user.firebase_user_id = firebase_user_id
    user.first_name = firebase_user_id
    user.last_name = 'User'
    user.email = f'{firebase_user_id}@email.com'
    user.is_active = True
    user.is_coach = is_coach
    user.is_client = is_client
    user.is_admin = is_admin
    session.add(user)
    session.flush()
    return user


def _post_as(client, user, path, payload):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.post(path, json=payload, headers={'Authorization': 'Bearer token'})


def _get_as(client, user, path):
    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': user.firebase_user_id}
        return client.get(path, headers={'Authorization': 'Bearer token'})


def test_coach_assignment_uses_workout_plan_clients_table(client, session):
    coach = _create_user(session, 'coach-user', is_coach=True, is_client=False)
    assigned_client = _create_user(session, 'client-user', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = assigned_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Client User'
    billing.card_address_1 = '123 St'
    billing.card_city = 'City'
    billing.card_postcode = '00000'
    billing.renew_day_number = 1
    session.add(billing)
    session.flush()

    link = ClientCoaches()
    link.client_id = assigned_client.user_id
    link.coach_id = coach.user_id
    link.client_billing_id = billing.client_billing_id
    session.add(link)

    plan = WorkoutPlans()
    plan.title = 'Coach Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.commit()

    payload = {
        'client_id': str(assigned_client.user_id),
        'assignments': [{'weekday': 'Wednesday', 'schedule_time': '09:00:00'}],
    }
    response = _post_as(client, coach, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
    body = response.get_json()

    assert response.status_code == 201
    assert body['client_id'] == str(assigned_client.user_id)
    assert len(body['assignments']) == 1

    assignment = (
        session.query(WorkoutPlanClients)
        .filter(
            WorkoutPlanClients.workout_plan_id == plan.workout_plan_id,
            WorkoutPlanClients.client_id == assigned_client.user_id,
            WorkoutPlanClients.unassigned_at.is_(None),
        )
        .first()
    )
    assert assignment is not None
    rows = session.query(WorkoutPlanClientDays).filter(WorkoutPlanClientDays.assignment_id == assignment.assignment_id).all()
    assert len(rows) == 1
    assert rows[0].weekday == 'Wednesday'


def test_non_roster_assignment_falls_back_to_plan_days(client, session):
    coach = _create_user(session, 'coach-fallback', is_coach=True, is_client=False)
    other_user = _create_user(session, 'other-user', is_coach=False, is_client=True)

    plan = WorkoutPlans()
    plan.title = 'Fallback Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.commit()

    payload = {
        'client_id': str(other_user.user_id),
        'assignments': [{'weekday': 'Friday', 'schedule_time': '07:30:00'}],
    }
    response = _post_as(client, coach, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
    body = response.get_json()
    assert response.status_code == 201
    assert body['workout_plan_id'] == plan.workout_plan_id

    plan_days = session.query(WorkoutPlanDays).filter(WorkoutPlanDays.workout_plan_id == plan.workout_plan_id).all()
    assert len(plan_days) == 1
    assignments = session.query(WorkoutPlanClients).filter(WorkoutPlanClients.workout_plan_id == plan.workout_plan_id).all()
    assert len(assignments) == 0


def test_weekly_schedule_includes_client_assignments_and_get_workouts_stays_real_only(client, session):
    coach = _create_user(session, 'coach-weekly', is_coach=True, is_client=False)
    assigned_client = _create_user(session, 'client-weekly', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = assigned_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Client Weekly'
    billing.card_address_1 = '123 St'
    billing.card_city = 'City'
    billing.card_postcode = '00000'
    billing.renew_day_number = 1
    session.add(billing)
    session.flush()

    link = ClientCoaches()
    link.client_id = assigned_client.user_id
    link.coach_id = coach.user_id
    link.client_billing_id = billing.client_billing_id
    session.add(link)

    plan = WorkoutPlans()
    plan.title = 'Weekly Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.flush()

    assignment = WorkoutPlanClients()
    assignment.workout_plan_id = plan.workout_plan_id
    assignment.client_id = assigned_client.user_id
    assignment.assigned_by = coach.user_id
    session.add(assignment)
    session.flush()

    day = WorkoutPlanClientDays()
    day.assignment_id = assignment.assignment_id
    day.weekday = 'Monday'
    day.schedule_time = time(8, 0, 0)
    session.add(day)
    session.commit()

    weekly = _get_as(client, assigned_client, f'/workouts/weekly-assignments?user_id={assigned_client.user_id}')
    weekly_body = weekly.get_json()
    assert weekly.status_code == 200
    assert len(weekly_body) == 1
    assert weekly_body[0]['workout_plan_id'] == plan.workout_plan_id
    assert weekly_body[0]['assignment_id'] == assignment.assignment_id

    workouts = _get_as(client, assigned_client, f'/workouts?user_id={assigned_client.user_id}')
    assert workouts.status_code == 200
    assert workouts.get_json() == []
