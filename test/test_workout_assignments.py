from datetime import time
from util import create_user, post_as, get_as, delete_as

from models import *

def test_coach_assignment_uses_workout_plan_clients_table(client, session):
    coach = create_user(session, 'coach-user', is_coach=True, is_client=False)
    assigned_client = create_user(session, 'client-user', is_coach=False, is_client=True)

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
    response = post_as(client, coach, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
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
    coach = create_user(session, 'coach-fallback', is_coach=True, is_client=False)
    other_user = create_user(session, 'other-user', is_coach=False, is_client=True)

    plan = WorkoutPlans()
    plan.title = 'Fallback Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.commit()

    payload = {
        'client_id': str(other_user.user_id),
        'assignments': [{'weekday': 'Friday', 'schedule_time': '07:30:00'}],
    }
    response = post_as(client, coach, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
    body = response.get_json()
    assert response.status_code == 201
    assert body['workout_plan_id'] == plan.workout_plan_id

    plan_days = session.query(WorkoutPlanDays).filter(WorkoutPlanDays.workout_plan_id == plan.workout_plan_id).all()
    assert len(plan_days) == 1
    assignments = session.query(WorkoutPlanClients).filter(WorkoutPlanClients.workout_plan_id == plan.workout_plan_id).all()
    assert len(assignments) == 0


def test_weekly_schedule_includes_client_assignments_and_get_workouts_stays_real_only(client, session):
    coach = create_user(session, 'coach-weekly', is_coach=True, is_client=False)
    assigned_client = create_user(session, 'client-weekly', is_coach=False, is_client=True)

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

    weekly = get_as(client, assigned_client, f'/workouts/weekly-assignments?user_id={assigned_client.user_id}')
    weekly_body = weekly.get_json()
    assert weekly.status_code == 200
    assert len(weekly_body) == 1
    assert weekly_body[0]['workout_plan_id'] == plan.workout_plan_id
    assert weekly_body[0]['assignment_id'] == assignment.assignment_id

    workouts = get_as(client, assigned_client, f'/workouts?user_id={assigned_client.user_id}')
    assert workouts.status_code == 200
    assert workouts.get_json() == []


def test_available_workout_plans_unions_created_and_assigned(client, session):
    coach = create_user(session, 'coach-available', is_coach=True, is_client=False)
    target_client = create_user(session, 'client-available', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = target_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Client Available'
    billing.card_address_1 = '123 St'
    billing.card_city = 'City'
    billing.card_postcode = '00000'
    billing.renew_day_number = 1
    session.add(billing)
    session.flush()

    link = ClientCoaches()
    link.client_id = target_client.user_id
    link.coach_id = coach.user_id
    link.client_billing_id = billing.client_billing_id
    session.add(link)

    client_created_plan = WorkoutPlans()
    client_created_plan.title = 'Client Created Plan'
    client_created_plan.created_by = target_client.user_id
    session.add(client_created_plan)
    session.flush()

    coach_plan = WorkoutPlans()
    coach_plan.title = 'Coach Assigned Plan'
    coach_plan.created_by = coach.user_id
    session.add(coach_plan)
    session.flush()

    assignment = WorkoutPlanClients()
    assignment.workout_plan_id = coach_plan.workout_plan_id
    assignment.client_id = target_client.user_id
    assignment.assigned_by = coach.user_id
    session.add(assignment)

    global_plan = WorkoutPlans()
    global_plan.title = 'Global Template'
    global_plan.created_by = None
    session.add(global_plan)
    session.commit()

    available = get_as(client, target_client, '/workout-plans/available')
    body = available.get_json()
    assert available.status_code == 200
    assert len(body) == 3

    by_title = {row['title']: row for row in body}
    assert by_title['Client Created Plan']['is_created_by_user'] is True
    assert by_title['Client Created Plan']['is_assigned_to_user'] is False
    assert by_title['Client Created Plan']['is_global_template'] is False
    assert by_title['Coach Assigned Plan']['is_created_by_user'] is False
    assert by_title['Coach Assigned Plan']['is_assigned_to_user'] is True
    assert by_title['Coach Assigned Plan']['is_global_template'] is False
    assert by_title['Global Template']['created_by'] is None
    assert by_title['Global Template']['is_global_template'] is True
    assert by_title['Global Template']['is_created_by_user'] is False
    assert by_title['Global Template']['is_assigned_to_user'] is False


def test_global_plan_can_be_assigned_to_self(client, session):
    user = create_user(session, 'global-self-user', is_coach=False, is_client=True)

    plan = WorkoutPlans()
    plan.title = 'Global Self Plan'
    plan.created_by = None
    session.add(plan)
    session.commit()

    payload = {'assignments': [{'weekday': 'Monday', 'schedule_time': '08:00:00'}]}
    response = post_as(client, user, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
    body = response.get_json()

    assert response.status_code == 201
    assert body['workout_plan_id'] == plan.workout_plan_id
    plan_days = session.query(WorkoutPlanDays).filter(WorkoutPlanDays.workout_plan_id == plan.workout_plan_id).all()
    assert len(plan_days) == 1
    assert plan_days[0].weekday == 'Monday'


def test_coach_can_assign_global_plan_to_client(client, session):
    coach = create_user(session, 'global-coach-user', is_coach=True, is_client=False)
    assigned_client = create_user(session, 'global-client-user', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = assigned_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Global Client'
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
    plan.title = 'Global Coach Assign Plan'
    plan.created_by = None
    session.add(plan)
    session.commit()

    payload = {
        'client_id': str(assigned_client.user_id),
        'assignments': [{'weekday': 'Wednesday', 'schedule_time': '09:00:00'}],
    }
    response = post_as(client, coach, f'/workout-plans/{plan.workout_plan_id}/assignments', payload)
    body = response.get_json()

    assert response.status_code == 201
    assert body['workout_plan_id'] == plan.workout_plan_id
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


def test_assigned_client_can_get_workout_plan_details(client, session):
    coach = create_user(session, 'coach-details', is_coach=True, is_client=False)
    assigned_client = create_user(session, 'client-details', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = assigned_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Client Details'
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
    plan.title = 'Assigned Detail Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.flush()

    assignment = WorkoutPlanClients()
    assignment.workout_plan_id = plan.workout_plan_id
    assignment.client_id = assigned_client.user_id
    assignment.assigned_by = coach.user_id
    session.add(assignment)
    session.flush()

    assignment_day = WorkoutPlanClientDays()
    assignment_day.assignment_id = assignment.assignment_id
    assignment_day.weekday = 'Tuesday'
    assignment_day.schedule_time = time(7, 30, 0)
    session.add(assignment_day)
    session.commit()

    response = get_as(client, assigned_client, f'/workout-plans/{plan.workout_plan_id}')
    body = response.get_json()

    assert response.status_code == 200
    assert body['workout_plan_id'] == plan.workout_plan_id
    assert len(body['assignments']) == 1
    assert body['assignments'][0]['assignment_id'] == assignment.assignment_id
    assert body['assignments'][0]['weekday'] == 'Tuesday'


def test_delete_plan_assignment_supports_client_assignment_days(client, session):
    coach = create_user(session, 'coach-delete-clientday', is_coach=True, is_client=False)
    assigned_client = create_user(session, 'client-delete-clientday', is_coach=False, is_client=True)

    billing = ClientBilling()
    billing.client_id = assigned_client.user_id
    billing.card_number = '4111111111111111'
    billing.card_exp_month = 1
    billing.card_exp_year = 2030
    billing.card_security_number = 111
    billing.card_name = 'Client Delete'
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
    plan.title = 'Delete Assigned Day Plan'
    plan.created_by = coach.user_id
    session.add(plan)
    session.flush()

    assignment = WorkoutPlanClients()
    assignment.workout_plan_id = plan.workout_plan_id
    assignment.client_id = assigned_client.user_id
    assignment.assigned_by = coach.user_id
    session.add(assignment)
    session.flush()

    assignment_day = WorkoutPlanClientDays()
    assignment_day.assignment_id = assignment.assignment_id
    assignment_day.weekday = 'Thursday'
    assignment_day.schedule_time = time(9, 0, 0)
    session.add(assignment_day)
    session.commit()

    response = delete_as(client, assigned_client, f'/workout-plan-assignments/{assignment_day.id}')
    assert response.status_code == 200
    remaining = session.query(WorkoutPlanClientDays).filter(WorkoutPlanClientDays.id == assignment_day.id).first()
    assert remaining is None
