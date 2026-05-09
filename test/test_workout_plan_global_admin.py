"""Admin-only global workout plan listing and creation endpoints."""

from models import WorkoutPlans
from util import create_user, get_as, patch_as, post_as


def test_get_workout_plans_global_lists_only_templates_and_requires_admin(client, session):
    admin = create_user(session, 'global-list-admin', is_admin=True)
    regular = create_user(session, 'global-list-regular', is_admin=False)

    owned = WorkoutPlans()
    owned.title = 'Owned Plan'
    owned.created_by = regular.user_id
    session.add(owned)

    global_plan = WorkoutPlans()
    global_plan.title = 'A Global Plan'
    global_plan.created_by = None
    session.add(global_plan)
    session.commit()

    denied = get_as(client, regular, '/workout-plans/global')
    assert denied.status_code == 401

    ok = get_as(client, admin, '/workout-plans/global')
    assert ok.status_code == 200
    body = ok.get_json()
    assert len(body) == 1
    assert body[0]['title'] == 'A Global Plan'
    assert body[0]['created_by'] is None
    assert body[0]['workout_plan_id'] == global_plan.workout_plan_id


def test_post_workout_plans_global_creates_template_and_requires_admin(client, session):
    admin = create_user(session, 'global-post-admin', is_admin=True)
    user = create_user(session, 'global-post-user', is_admin=False)

    denied = post_as(
        client, user, '/workout-plans/global', {'title': 'Should Fail'},
    )
    assert denied.status_code == 401

    created = post_as(
        client,
        admin,
        '/workout-plans/global',
        {'title': 'Admin Global', 'description': 'd', 'duration_min': 45},
    )
    assert created.status_code == 201
    wid = created.get_json()['workout_plan_id']
    row = session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == wid).first()
    assert row is not None
    assert row.title == 'Admin Global'
    assert row.created_by is None


def test_patch_created_by_null_requires_admin_to_promote_to_global(client, session):
    admin = create_user(session, 'global-patch-admin', is_admin=True)
    owner = create_user(session, 'global-patch-owner', is_admin=False)

    plan = WorkoutPlans()
    plan.title = 'Promote Me'
    plan.created_by = owner.user_id
    session.add(plan)
    session.commit()

    bad = patch_as(
        client,
        owner,
        f'/workout-plans/{plan.workout_plan_id}',
        {'created_by': None},
    )
    assert bad.status_code == 403

    good = patch_as(
        client,
        admin,
        f'/workout-plans/{plan.workout_plan_id}',
        {'created_by': None},
    )
    assert good.status_code == 200
    session.refresh(plan)
    assert plan.created_by is None
