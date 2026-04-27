from datetime import date, datetime, timezone, timedelta
from enum import Enum
from uuid import UUID

from models import *
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g
from sqlalchemy import func

from auth.util import can_access_client_endpoint 

def _build_coach_json(coach):

    survey = coach[0].coach_surveys[0] if coach[0].coach_surveys else None

    specialization = survey.specialization if survey else None
    qualifications = survey.qualifications if survey else None

    return {
        'coach_user_id': coach[0].user_id,
        'first_name': coach[0].first_name,
        'last_name': coach[0].last_name,
        'coach_cost': coach[0].coach_cost,
        'avg_rating': coach[1],
        'qualifications': qualifications,
        'is_exercise_specialization': specialization in ('EXERCISE', 'BOTH'),
        'is_nutrition_specialization': specialization in ('NUTRITION', 'BOTH'),
    }

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
    """
    Get a list of a user's coaches
    ---
    tags:
        - Clients
    responses:
        200:
            description: List of all coaches
            schema:
                type: array
                items:
                    type: object
                    properties:
                        coach_user_id:
                            type: integer
                        first_name:
                            type: string
                        last_name:
                            type: string
                        coach_cost:
                            type: integer
                        avg_rating:
                            type: integer
                        is_exercise_specialization:
                            type: boolean
                        is_nutrition_specialization:
                            type: boolean
        400:
            description: UUID is invalid
    """
    user = g.user

    try:
        user_id = UUID(user_id)
    except (ValueError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if user.user_id != user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 401

    avg_ratings = db.session.query(CoachReviews.coach_id, func.avg(CoachReviews.rating).label('avg_rating')) \
        .group_by(CoachReviews.coach_id) \
        .subquery()

    coaches = db.session.query(Users, func.coalesce(avg_ratings.c.avg_rating, 5)) \
        .join(ClientCoaches, ClientCoaches.coach_id == Users.user_id) \
        .outerjoin(avg_ratings, Users.user_id == avg_ratings.c.coach_id) \
        .join(CoachSurveys) \
        .filter(ClientCoaches.client_id == user_id) \
        .filter(Users.is_active == True) \
        .filter(Users.is_coach == True) \
        .order_by(func.coalesce(avg_ratings.c.avg_rating, 0).desc())

    return jsonify({
        'coaches': [_build_coach_json(c) for c in coaches]
    })



@client_blueprint.route('/<user_id>/current_goals')
@require_auth
def get_current_goals(user_id):
    """
    Get the current goals for a client
    ---
    tags:
        - Clients
    responses:
        200:
            description: Latest client survey
            schema:
                type: object
                properties:
                    user_survey_id:
                        type: integer
                    primary_goals_binary:
                        type: string
                        description: |
                            Primary goals are stored as a binary string where the digits at each offset represent.
                            0: Lose weight
                            1: Build muscle
                            2: Increase strength
                            3: Improve endurance
                            4: General fitness
                            5: Sports performance
                    weight_goal:
                        type: integer
                    exercise_minutes_goal:
                        type: integer
                    personal_goals:
                        type: string
                    date_created:
                        type: string
                    last_updated:
                        type: string
        400:
            description: Invalid UUID
        404:
            description: No client survey found for user
    """
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
    """
    Submit initial goal survey on registration
    ---
    tags:
        - Clients
    parameters:
        - name: body
          in: body
          required: true
          schema:
            required:
                - name
            properties:
                primary_goals_binary:
                    type: string
                    required: true
                weight_goal:
                    type: integer
                    required: true
                exercise_minutes_goal:
                    type: integer
                    required: true
                personal_goals:
                    type: string
                    required: true
    responses:
        201:
            description: Submit initial goal survey on onboarding
            schema:
                type: object
                properties:
                    user_survey_id:
                        type: integer
                    primary_goals_binary:
                        type: string
                        description: |
                            Primary goals are stored as a binary string where the digits at each offset represent.
                            0: Lose weight
                            1: Build muscle
                            2: Increase strength
                            3: Improve endurance
                            4: General fitness
                            5: Sports performance
                    weight_goal:
                        type: integer
                    exercise_minutes_goal:
                        type: integer
                    personal_goals:
                        type: string
                    date_created:
                        type: string
                    last_updated:
                        type: string
        400:
            description: Invalid UUID
        409:
            description: User already has completed the initial goal survey.
    """

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
    """
    Edit goal survey
    ---
    tags:
        - Clients
    parameters:
        - name: body
          in: body
          required: true
          schema:
            required:
                - name
            properties:
                primary_goals_binary:
                    type: string
                    required: false
                weight_goal:
                    type: integer
                    required: false
                exercise_minutes_goal:
                    type: integer
                    required: false
                personal_goals:
                    type: string
                    required: false
    responses:
        200:
            description: Edited goal survey
            schema:
                type: object
                properties:
                    user_survey_id:
                        type: integer
                    primary_goals_binary:
                        type: string
                    weight_goal:
                        type: integer
                    exercise_minutes_goal:
                        type: integer
                    personal_goals:
                        type: string
                    date_created:
                        type: string
                    last_updated:
                        type: string
        400:
            description: Invalid UUID
        404:
            description: Client has no existing survey to update

    """
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
    """
    Get user goals
    ---
    tags:
        - Clients
    parameters:
        - name: limit
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get workout plan exercises
            schema:
                type: object
                properties:
                    user_survey_id:
                        type: integer
                    primary_goals_binary:
                        type: string
                    weight_goal:
                        type: integer
                    exercise_minutes_goal:
                        type: integer
                    personal_goals:
                        type: string
                    date_created:
                        type: string
                    last_updated:
                        type: string
        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
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
    """
    Get daily survey history
    ---
    tags:
        - Clients
    parameters:
        - name: days
          description: Number of days between 1 and 365
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Daily survey history
            schema:
                type: array
                items:
                    type: object
                    properties:
                        daily_survey_id:
                            type: integer
                        mood:
                            type: integer
                        energy:
                            type: integer
                        sleep:
                            type: integer
                        notes:
                            type: string
                        date_submitted:
                            type: string
        400:
            description: Invalid UUID or day
    """
    try:
        requested_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'error': 'invalid uuid'}), 400

    if not can_access_client_endpoint(g.user, requested_user_id, g.clients_ids):
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
    """
        Get current daily survey
        ---
        tags:
            - Clients
        responses:
            200:
                description: Current daily survey
                schema:
                    type: object
                    properties:
                        daily_survey_id:
                            type: integer
                        mood:
                            type: integer
                        energy:
                            type: integer
                        sleep:
                            type: integer
                        notes:
                            type: string
                        date_submitted:
                            type: string
            404:
                description: User has not submitted a daily survey for today
        """
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
    """
    Submit daily survey
    ---
    tags:
        - Clients
    parameters:
        - name: body
          in: body
          required: true
          schema:
            required:
                - name
            properties:
                mood:
                    type: integer
                    required: true
                energy:
                    type: integer
                    required: true
                sleep:
                    type: integer
                    required: true
                notes:
                    type: string
    responses:
        201:
            description: Submit initial goal survey on onboarding
            schema:
                type: object
                properties:
                    daily_survey_id:
                        type: integer
                    mood:
                        type: integer
                    energy:
                        type: integer
                    sleep:
                        type: integer
                    notes:
                        type: string
                    date_submitted:
                        type: string
        400:
            description: Missing parameters
        409:
            description: User already submitted a daily survey for today
    """
    user = g.user
    mood = request.json['mood']
    energy = request.json['energy']
    sleep = request.json['sleep']
    notes = request.json['notes']

    if mood is None or energy is None or sleep is None:
        return jsonify({'error': 'JSON must contain mood, energy, sleep, and notes'}), 400

    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.user_id == user_id).filter(DailySurveyResponses.date_submitted == date.today()).first())

    if survey is not None:
        return jsonify([{'error': 'User already submitted a daily survey for today. Edit using edit endpoint.'}]), 409
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
    """
        Edit daily survey
        ---
        tags:
            - Clients
        parameters:
            - name: body
              in: body
              required: true
              schema:
                required:
                    - name
                properties:
                    survey_id:
                        type: integer
                        required: true
                    mood:
                        type: integer
                        required: false
                    energy:
                        type: integer
                        required: false
                    sleep:
                        type: integer
                        required: false
                    notes:
                        type: string
        responses:
            200:
                description: Submit initial goal survey on onboarding
                schema:
                    type: object
                    properties:
                        daily_survey_id:
                            type: integer
                        mood:
                            type: integer
                        energy:
                            type: integer
                        sleep:
                            type: integer
                        notes:
                            type: string
            404:
                description: Daily survey does not exist
        """
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
