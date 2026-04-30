from util import create_user, post_as, get_as
from models import *

def test_visitors_top_coaches(client, session):
    user = create_user(session, 'reviewer')
    coach1 = create_user(session, 'coach1', is_coach=True)
    coach2 = create_user(session, 'coach2', is_coach=True)

    cs1 = CoachSurveys()
    cs1.user_id = coach1.user_id
    cs1.specialization = 'BOTH'
    cs1.qualifications = ''

    cs2 = CoachSurveys()
    cs2.user_id = coach2.user_id
    cs2.specialization = 'BOTH'
    cs2.qualifications = ''

    session.add_all([cs1, cs2])

    cr1 = CoachReviews()
    cr1.left_by_user_id = user.user_id
    cr1.coach_id = coach1.user_id
    cr1.rating = 10

    cr2 = CoachReviews()
    cr2.left_by_user_id = user.user_id
    cr2.coach_id = coach1.user_id
    cr2.rating = 8

    cr3 = CoachReviews()
    cr3.left_by_user_id = user.user_id
    cr3.coach_id = coach2.user_id
    cr3.rating = 7

    session.add_all([cr1, cr2, cr3])
    session.commit()

    response = client.get('/visitors/top_coaches?limit=10')

    assert response.status_code == 200

    data = response.get_json()
    assert 'coaches' in data
    assert data['total_results'] >= 2

    assert data['coaches'][0]['first_name'] == coach1.first_name

def test_visitors_top_coaches_missing(client, session):
    response = client.get('/visitors/top_coaches')

    assert response.status_code == 400
    assert 'limit parameter' in response.get_json()['message']

def test_visitors_exercise_categories(client, session):
    ec1 = ExerciseCategories()
    ec1.name = 'Cardio'

    ec2 = ExerciseCategories()
    ec2.name = 'Lifting'

    ec3 = ExerciseCategories()
    ec3.name = 'Boxing'
    session.add_all([ec1, ec2, ec3])
    session.commit()

    response = client.get('/visitors/exercise-categories')

    assert response.status_code == 200
    data = response.get_json()
    names = [c['name'] for c in data]

    assert names == sorted(names)

def test_body_parts(client, session):

    bp1 = BodyParts()
    bp1.name = 'Legs'

    bp2 = BodyParts()
    bp2.name = 'Arms'

    bp3 = BodyParts()
    bp3.name = 'Back'

    session.add_all([bp1, bp2, bp3])
    session.commit()

    response = client.get("/visitors/body-parts")

    assert response.status_code == 200

    data = response.get_json()

    names = [b["name"] for b in data]

    assert names == sorted(names)

def test_exercises(client, session):
    category = ExerciseCategories()
    category.name = 'Strength'

    body_part = BodyParts()
    body_part.name = 'Legs'

    session.add_all([category, body_part])
    session.commit()

    exercise = Exercises()
    exercise.name="Squat"
    exercise.youtube_url="https://youtube.com/squat"
    exercise.body_part_id=body_part.body_part_id
    exercise.category_id=category.category_id

    session.add(exercise)
    session.commit()

    response = client.get("/visitors/exercises")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1

    e = data[0]
    assert e["name"] == "Squat"
    assert e["body_part"] == "Legs"
    assert e["category"] == "Strength"