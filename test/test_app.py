import uuid
from unittest.mock import patch
from models import *


def test_root(client, session):

    def make_data(name):
        c = ExerciseCategories()
        c.name = name
        session.add(c)
        session.commit()

    make_data('Assisted Bodyweight')
    make_data('Barbell')
    make_data('Cardio')
    make_data('Dumbbell')
    make_data('Duration')
    make_data('Machine/Other')
    make_data('Reps Only')
    make_data('Weighted Bodyweight')

    response = client.get('/')

    assert response.get_json() == [
    {
        'name': 'Assisted Bodyweight'
    },
    {
        'name': 'Barbell'
    },
    {
        'name': 'Cardio'
    },
    {
        'name': 'Dumbbell'
    },
    {
        'name': 'Duration'
    },
    {
        'name': 'Machine/Other'
    },
    {
        'name': 'Reps Only'
    },
    {
        'name': 'Weighted Bodyweight'
    }
]


def test_authtest_no_auth_header(client):
    response = client.get('/authtest')
    assert response.status_code == 401


def test_authtest_client(client, session):
    user = Users()
    user.user_id = uuid.uuid4()
    user.firebase_user_id = 'test-client'
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.email = 'john.doe@email.com'
    user.is_active = True
    user.is_coach = False
    user.is_client = True

    session.add(user)
    session.commit()

    with patch('auth.authentication.auth.verify_id_token') as mock_fb:
        mock_fb.return_value = {'uid': 'test-client', 'email': 'john.doe@email.com'}

        headers = {'Authorization': 'Bearer token'}
        response = client.get('/authtest', headers=headers)

        assert response.status_code == 200
        assert 'John' in response.json['message']


def test_error_404(client):
    response = client.get('/nonexistent')
    assert response.status_code == 404
    assert response.get_json() == {'message': 'That resource cannot be found'}

def test_error_405(client):
    response = client.post('/')
    assert response.status_code == 405
    assert response.get_json() == {'message': 'HTTP method is not allowed on that resource'}

def test_error_500(app, client):
    app.config['PROPAGATE_EXCEPTIONS'] = False

    @app.route('/500-test')
    def error_500():
        raise Exception()

    response = client.get('/500-test')
    assert response.status_code == 500
    assert 'An internal error occurred. Please try again later.' in response.get_json()['message']

    app.config['PROPAGATE_EXCEPTIONS'] = True