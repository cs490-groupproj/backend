from datetime import date, datetime, timezone, timedelta
from enum import Enum
from uuid import UUID

from models import *
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g

client_blueprint = Blueprint('client_blueprint', __name__)

_PRIMARY_GOALS_BINARY_CHARS = {'0', '1'}


def _validate_primary_goals_binary(value):
    if value is None:
        return None, False
    if len(value) != 6 or not set(value).issubset(_PRIMARY_GOALS_BINARY_CHARS):
        return jsonify({
            'error': 'Primary goals are not valid. Use a 6-character string of 0 and 1.',
            'hint': {
                'string': '110000',
                'meaning': 'represents offset 0 and 1 as selected',
                'offset_key': {
                    0: 'Lose Weight',
                    1: 'Build Muscle',
                    2: 'Increase Strength',
                    3: 'Improve Endurance',
                    4: 'General Fitness',
                    5: 'Sports Performance',
                },
            },
        }), True
    return None, False


def _latest_client_survey(user_id):
    return (
        db.session.query(ClientGoals)
        .filter(ClientGoals.user_id == user_id)
        .order_by(ClientGoals.date_created.desc())
        .first()
    )


def _now_naive_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _require_client_role():
    # Dual-role users are valid here; the only disallowed case is not-a-client.
    if not bool(getattr(g.user, 'is_client', False)):
        return jsonify({'error': 'Client survey endpoints are only for users with is_client=true'}), 403
    return None


@client_blueprint.route('/<user_id>/coaches')
@require_auth
def coaches(user_id):
    user = g.user

    try:
        user_id = UUID(user_id)
    except (ValueError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if user.user_id != user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 401

    relationships = db.session.query(ClientCoaches).filter(ClientCoaches.client_id == user_id)

    return jsonify({
        'coaches': [{
            'id': r.coach_id,
            'first_name': r.coach.first_name,
            'last_name': r.coach.last_name
        } for r in relationships]
    })



@client_blueprint.route('/<user_id>/current_goals')
@require_auth
def get_current_goals(user_id):
    role_err = _require_client_role()
    if role_err is not None:
        return role_err

    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if requested_user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 403

    current_goals = _latest_client_survey(g.user.user_id)
    if current_goals is None:
        return jsonify({'error': 'No client survey found for this user'}), 404

    return jsonify({
        'user_survey_id': current_goals.user_survey_id,
        'primary_goals_binary': current_goals.primary_goals,
        'weight_goal': current_goals.weight_goal,
        'exercise_minutes_goal': current_goals.exercise_minutes_goal,
        'personal_goals': current_goals.personal_goals,
        'date_created': current_goals.date_created.isoformat() if current_goals.date_created else None,
        'last_updated': current_goals.last_updated.isoformat() if current_goals.last_updated else None,
    }), 200


# Primary goals are stored as a binary string where the digits at each offset represent:
# 0: Lose weight
# 1: Build muscle
# 2: Increase strength
# 3: Improve endurance
# 4: General fitness
# 5: Sports performance
# The binary string 110000 means the user has selected Lose weight and Build muscle

@client_blueprint.route('/<user_id>/initial_goal_survey', methods=['POST'])
@require_auth
def add_initial_goals(user_id):
    role_err = _require_client_role()
    if role_err is not None:
        return role_err

    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if requested_user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to create this content'}), 403

    if db.session.query(ClientGoals).filter(ClientGoals.user_id == g.user.user_id).count() > 0:
        return jsonify({'error': 'User already has completed the initial goal survey.'}), 409

    body = request.get_json(silent=True) or {}
    err, invalid = _validate_primary_goals_binary(body.get('primary_goals_binary'))
    if invalid:
        return err, 400

    new_goal = ClientGoals()
    new_goal.user_id = g.user.user_id
    new_goal.primary_goals = body.get('primary_goals_binary')
    new_goal.weight_goal = body.get('weight_goal') if body.get('weight_goal') is not None else body.get('weight')
    new_goal.exercise_minutes_goal = body.get('exercise_minutes_goal') if body.get('exercise_minutes_goal') is not None else body.get('exercise_minutes')
    new_goal.personal_goals = body.get('personal_goals')
    new_goal.last_updated = _now_naive_utc()

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'user_survey_id': new_goal.user_survey_id,
        'primary_goals_binary': new_goal.primary_goals,
        'weight_goal': new_goal.weight_goal,
        'exercise_minutes_goal': new_goal.exercise_minutes_goal,
        'personal_goals': new_goal.personal_goals,
        'date_created': new_goal.date_created.isoformat() if new_goal.date_created else None,
        'last_updated': new_goal.last_updated.isoformat() if new_goal.last_updated else None,
    }), 201


@client_blueprint.route('/<user_id>/edit_goals', methods=['PATCH'])
@require_auth
def edit_goals(user_id):
    role_err = _require_client_role()
    if role_err is not None:
        return role_err

    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if requested_user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to modify this content'}), 403

    body = request.get_json(silent=True) or {}
    survey = _latest_client_survey(g.user.user_id)
    if survey is None:
        return jsonify({'error': 'No client survey to update. Use POST /clients/<user_id>/initial_goal_survey first.'}), 404

    if 'primary_goals_binary' in body:
        err, invalid = _validate_primary_goals_binary(body.get('primary_goals_binary'))
        if invalid:
            return err, 400
        survey.primary_goals = body.get('primary_goals_binary')
    if 'weight_goal' in body:
        survey.weight_goal = body['weight_goal']
    elif 'weight' in body:
        survey.weight_goal = body['weight']
    if 'exercise_minutes_goal' in body:
        survey.exercise_minutes_goal = body['exercise_minutes_goal']
    elif 'exercise_minutes' in body:
        survey.exercise_minutes_goal = body['exercise_minutes']
    if 'personal_goals' in body:
        survey.personal_goals = body['personal_goals']

    survey.last_updated = _now_naive_utc()
    db.session.commit()

    return jsonify({
        'user_survey_id': survey.user_survey_id,
        'primary_goals_binary': survey.primary_goals,
        'weight_goal': survey.weight_goal,
        'exercise_minutes_goal': survey.exercise_minutes_goal,
        'personal_goals': survey.personal_goals,
        'date_created': survey.date_created.isoformat() if survey.date_created else None,
        'last_updated': survey.last_updated.isoformat() if survey.last_updated else None,
    }), 200


@client_blueprint.route('/<user_id>/historical_goals')
@require_auth
def get_goals(user_id):
    role_err = _require_client_role()
    if role_err is not None:
        return role_err

    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if requested_user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 403

    limit = request.args.get('limit', type=int)
    q = db.session.query(ClientGoals).filter(ClientGoals.user_id == g.user.user_id).order_by(ClientGoals.date_created.desc())
    if limit is not None:
        q = q.limit(limit)
    all_goals = q.all()

    return jsonify([{
        'user_survey_id': g.user_survey_id,
        'primary_goals_binary': g.primary_goals,
        'weight_goal': g.weight_goal,
        'exercise_minutes_goal': g.exercise_minutes_goal,
        'personal_goals': g.personal_goals,
        'date_created': g.date_created.isoformat() if g.date_created else None,
        'last_updated': g.last_updated.isoformat() if g.last_updated else None,
    } for g in all_goals]), 200

@client_blueprint.route('/<user_id>/daily_survey/history', methods=['GET'])
@require_auth
def get_daily_survey_history(user_id):
    role_err = _require_client_role()
    if role_err is not None:
        return role_err

    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if requested_user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 403

    days = request.args.get('days', default=7, type=int)
    if days is None or days < 1 or days > 366:
        return jsonify({'error': 'days must be an integer between 1 and 366'}), 400

    cutoff = date.today() - timedelta(days=days - 1)

    rows = (
        db.session.query(DailySurveyResponses)
        .filter(DailySurveyResponses.user_id == requested_user_id)
        .filter(DailySurveyResponses.date_submitted >= cutoff)
        .order_by(DailySurveyResponses.date_submitted.asc())
        .all()
    )

    return jsonify([{
        'daily_survey_id': r.daily_survey_response_id,
        'mood': r.mood,
        'energy': r.energy,
        'sleep': r.sleep,
        'notes': r.notes,
        'date_submitted': r.date_submitted.isoformat() if r.date_submitted else None,
    } for r in rows]), 200

@client_blueprint.route('/<user_id>/daily_survey/')
@require_auth
def get_daily_survey(user_id):
    user = g.user
    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.user_id == user_id).filter(DailySurveyResponses.date_submitted == date.today()))
    if survey is None:
        return jsonify([{'error': 'User has not yet submitted a daily survey for today'}]), 404
    elif survey.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to view this content'}]), 401
    else:
        return jsonify([{
            'daily_survey_id': survey.daily_survey_response_id,
            'mood': survey.mood,
            'energy': survey.energy,
            'sleep': survey.sleep,
            'notes': survey.notes,
            'date_submitted': survey.date_submitted
        }])

@client_blueprint.route('/<user_id>/daily_survey/submit', methods=['POST'])
@require_auth
def submit_daily_survey(user_id):
    user = g.user
    mood = request.json['mood']
    energy = request.json['energy']
    sleep = request.json['sleep']
    notes = request.json['notes']

    if mood is None or energy is None or sleep is None:
        return jsonify({'error': 'JSON must contain mood, energy, sleep, and notes'}), 400

    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.user_id == user_id).filter(DailySurveyResponses.date_submitted == date.today()).first())

    if survey is not None:
        return jsonify([{'error': 'User already submitted a daily survey for today. Edit using edit endpoint.'}]), 400
    else:
        new_survey = DailySurveyResponses()
        new_survey.user_id = user_id
        new_survey.mood = mood
        new_survey.energy = energy
        new_survey.sleep = sleep
        new_survey.notes = notes
        new_survey.date_submitted = date.today()
        db.session.add(new_survey)
        db.session.commit()

        return jsonify([{
            'daily_survey_id': new_survey.daily_survey_response_id,
            'mood': new_survey.mood,
            'energy': new_survey.energy,
            'sleep': new_survey.sleep,
            'notes': new_survey.notes,
            'date_submitted': new_survey.date_submitted

        }]), 201


@client_blueprint.route('/<user_id>/daily_survey/edit', methods=['PATCH'])
@require_auth
def edit_daily_survey(user_id):
    user = g.user
    survey_id = request.json['survey_id']
    mood = request.json['mood']
    notes = request.json['notes']
    energy = request.json.get('energy')
    sleep = request.json.get('sleep')

    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.daily_survey_response_id == survey_id).first())

    if survey is None:
        return jsonify([{'error': 'Daily survey does not exist.'}]), 404
    elif survey.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to modify this content'}]), 401
    else:
        survey.mood = mood or survey.mood
        survey.notes = notes or survey.notes
        if energy is not None:
            survey.energy = energy
        if sleep is not None:
            survey.sleep = sleep
        db.session.commit()

        return jsonify([{
            'daily_survey_id': survey.daily_survey_response_id,
            'mood': survey.mood,
            'energy': survey.energy,
            'sleep': survey.sleep,
            'notes': survey.notes
        }]), 200
