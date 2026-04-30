from util import create_user, delete_as, get_as, post_as, put_as

from models import BodyParts, ExerciseCategories, Exercises


def _seed_lookup_rows(session):
    chest = BodyParts()
    chest.name = 'Chest'
    back = BodyParts()
    back.name = 'Back'
    strength = ExerciseCategories()
    strength.name = 'Strength'
    cardio = ExerciseCategories()
    cardio.name = 'Cardio'
    session.add_all([chest, back, strength, cardio])
    session.commit()
    return chest, back, strength, cardio


def test_exercises_get_endpoints_are_accessible_for_non_admin(client, session):
    user = create_user(session, 'exercise-read-user', is_admin=False)
    chest, _, strength, _ = _seed_lookup_rows(session)

    ex = Exercises()
    ex.name = 'Bench Press'
    ex.youtube_url = 'https://example.com/bench'
    ex.body_part_id = chest.body_part_id
    ex.category_id = strength.category_id
    session.add(ex)
    session.commit()

    list_response = get_as(client, user, '/exercises')
    assert list_response.status_code == 200
    list_body = list_response.get_json()
    assert len(list_body) == 1
    assert list_body[0]['name'] == 'Bench Press'
    assert list_body[0]['body_part'] == 'Chest'
    assert list_body[0]['category'] == 'Strength'

    single_response = get_as(client, user, f'/exercises/{ex.exercise_id}')
    assert single_response.status_code == 200
    single_body = single_response.get_json()
    assert single_body['exercise_id'] == ex.exercise_id
    assert single_body['name'] == 'Bench Press'


def test_exercises_get_by_id_returns_404_for_missing_row(client, session):
    user = create_user(session, 'exercise-missing-user', is_admin=False)
    response = get_as(client, user, '/exercises/99999')
    assert response.status_code == 404
    assert response.get_json()['error'] == 'Exercise not found'


def test_exercises_post_is_admin_only(client, session):
    non_admin = create_user(session, 'exercise-create-non-admin', is_admin=False)
    chest, _, strength, _ = _seed_lookup_rows(session)

    response = post_as(
        client,
        non_admin,
        '/exercises',
        {
            'name': 'Push Up',
            'body_part_id': chest.body_part_id,
            'category_id': strength.category_id,
        },
    )
    assert response.status_code == 401
    assert response.get_json()['message'] == 'You are not authorized to access this content'


def test_exercises_post_admin_create_and_validate_fk(client, session):
    admin = create_user(session, 'exercise-create-admin', is_admin=True)
    chest, _, strength, _ = _seed_lookup_rows(session)

    invalid_fk_response = post_as(
        client,
        admin,
        '/exercises',
        {
            'name': 'Bad Exercise',
            'body_part_id': 999,
            'category_id': strength.category_id,
        },
    )
    assert invalid_fk_response.status_code == 400
    assert invalid_fk_response.get_json()['error'] == 'Invalid body_part_id'

    create_response = post_as(
        client,
        admin,
        '/exercises',
        {
            'name': 'Incline Bench Press',
            'youtube_url': 'https://example.com/incline',
            'body_part_id': chest.body_part_id,
            'category_id': strength.category_id,
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.get_json()['exercise_id']

    created = session.query(Exercises).filter(Exercises.exercise_id == created_id).first()
    assert created is not None
    assert created.name == 'Incline Bench Press'
    assert created.youtube_url == 'https://example.com/incline'


def test_exercises_put_admin_updates_and_put_non_admin_forbidden(client, session):
    admin = create_user(session, 'exercise-update-admin', is_admin=True)
    non_admin = create_user(session, 'exercise-update-non-admin', is_admin=False)
    chest, back, strength, cardio = _seed_lookup_rows(session)

    ex = Exercises()
    ex.name = 'Row'
    ex.youtube_url = None
    ex.body_part_id = chest.body_part_id
    ex.category_id = strength.category_id
    session.add(ex)
    session.commit()

    forbidden = put_as(
        client,
        non_admin,
        f'/exercises/{ex.exercise_id}',
        {'name': 'Should Not Work'},
    )
    assert forbidden.status_code == 401
    assert forbidden.get_json()['message'] == 'You are not authorized to access this content'

    invalid_category = put_as(
        client,
        admin,
        f'/exercises/{ex.exercise_id}',
        {'category_id': 999},
    )
    assert invalid_category.status_code == 400
    assert invalid_category.get_json()['error'] == 'Invalid category_id'

    updated = put_as(
        client,
        admin,
        f'/exercises/{ex.exercise_id}',
        {
            'name': 'Barbell Row',
            'youtube_url': 'https://example.com/row',
            'body_part_id': back.body_part_id,
            'category_id': cardio.category_id,
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()['message'] == 'Exercise updated'

    refreshed = session.query(Exercises).filter(Exercises.exercise_id == ex.exercise_id).first()
    assert refreshed.name == 'Barbell Row'
    assert refreshed.youtube_url == 'https://example.com/row'
    assert refreshed.body_part_id == back.body_part_id
    assert refreshed.category_id == cardio.category_id


def test_exercises_delete_admin_and_missing_row_behavior(client, session):
    admin = create_user(session, 'exercise-delete-admin', is_admin=True)
    chest, _, strength, _ = _seed_lookup_rows(session)

    ex = Exercises()
    ex.name = 'To Delete'
    ex.body_part_id = chest.body_part_id
    ex.category_id = strength.category_id
    session.add(ex)
    session.commit()

    delete_response = delete_as(client, admin, f'/exercises/{ex.exercise_id}')
    assert delete_response.status_code == 200
    assert delete_response.get_json()['message'] == 'Exercise deleted'

    gone = session.query(Exercises).filter(Exercises.exercise_id == ex.exercise_id).first()
    assert gone is None

    missing = delete_as(client, admin, f'/exercises/{ex.exercise_id}')
    assert missing.status_code == 404
    assert missing.get_json()['error'] == 'Exercise not found'
