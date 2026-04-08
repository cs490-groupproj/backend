from enum import Enum
from uuid import UUID

from models import *
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g
from datetime import date

client_blueprint = Blueprint('client_blueprint', __name__)

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
    user = g.user
    current_goals = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).first())

    if current_goals.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to view this content'}]), 401

    return jsonify({
        'primary_goals_binary': current_goals.primary_goals,
        'weight_goal': current_goals.weight_goal,
        'exercise_minutes_goal': current_goals.exercise_minutes_goal,
        'personal_goals': current_goals.personal_goals,
        'date_created': current_goals.date_created
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
    user = g.user

    if db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).count() > 0:
        return jsonify([{'error': 'User already has completed the initial goal survey.'}]), 403

    new_goal = ClientGoals()

    if UUID(user_id) != user.user_id:
        return jsonify([{'error': 'You are not authorized to create this content'}]), 401

    new_goal.user_id = UUID(user_id)

    binary_chars = {'0', '1'}
    if (new_primary_goals := request.json.get('primary_goals_binary')) is not None:
        if len(new_primary_goals) != 6 or not set(new_primary_goals).issubset(binary_chars):
            return jsonify([{
                'error': 'Primary goals are not valid. Use the primary goal binary system to refer to your goals.',
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

                    }
                }
            }]), 401
        else:
            new_goal.primary_goals = new_primary_goals

    if (new_weight := request.json.get('weight')) is not None:
        new_goal.weight_goal = new_weight
    if (new_exercise_minutes := request.json.get('exercise_minutes')) is not None:
        new_goal.exercise_minutes_goal = new_exercise_minutes
    if (new_personal_goals := request.json.get('personal_goals')) is not None:
        new_goal.personal_goals = new_personal_goals

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'primary_goals_binary': new_goal.primary_goals,
        'weight_goal': new_goal.weight_goal,
        'exercise_minutes_goal': new_goal.exercise_minutes_goal,
        'personal_goals': new_goal.personal_goals,
        'date_created': new_goal.date_created
    }), 200


@client_blueprint.route('/<user_id>/edit_goals', methods=['PATCH'])
@require_auth
def edit_goals(user_id):
    user = g.user

    old_goal = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).first())
    new_goal = ClientGoals()
    new_goal.user_id = UUID(user_id)

    if old_goal.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to modify this content'}]), 401

    if (new_primary_goals := request.json.get('primary_goals_binary')) is not None:
        binary_chars = {'0', '1'}
        if (new_primary_goals := request.json.get('primary_goals_binary')) is not None:
            if len(new_primary_goals) != 6 or not set(new_primary_goals).issubset(binary_chars):
                return jsonify([{
                    'error': 'Primary goals are not valid. Use the primary goal binary system to refer to your goals.',
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

                        }
                    }
                }]), 401
            else:
                new_goal.primary_goals = new_primary_goals
    else:
        new_primary_goals.primary_goals = old_goal.primary_goals

    if (new_weight := request.json.get('weight')) is not None:
        new_goal.weight_goal = new_weight
    else:
        new_goal.weight_goal = old_goal.weight_goal

    if (new_exercise_minutes := request.json.get('exercise_minutes')) is not None:
        new_goal.exercise_minutes_goal = new_exercise_minutes

    if (new_personal_goals := request.json.get('personal_goals')) is not None:
        new_goal.personal_goals = new_personal_goals
    else:
        new_goal.personal_goals = old_goal.personal_goals

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'primary_goals_binary': new_goal.primary_goals,
        'weight_goal': new_goal.weight_goal,
        'exercise_minutes_goal': new_goal.exercise_minutes_goal,
        'personal_goals': new_personal_goals,
    }), 200


@client_blueprint.route('/<user_id>/historical_goals')
@require_auth
def get_goals(user_id):
    user = g.user
    limit = request.args.get('limit', type=int)
    all_goals = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).limit(limit).all())
    for goal in all_goals:
        if goal.user_id != user.user_id:
            return jsonify([{'error': 'You are not authorized to view this content'}]), 401

    return jsonify([{
        'primary_goals_binary': g.primary_goals,
        'weight_goal': g.weight_goal,
        'exercise_minutes_goal': g.exercise_minutes_goal,
        'personal_goals': g.personal_goals,
        'date_created': g.date_created
    } for g in all_goals]), 200

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
            'feels_meeting_goals': survey.feels_meeting_goals
        }])

@client_blueprint.route('/<user_id>/daily_survey/submit', methods=['POST'])
@require_auth
def submit_daily_survey(user_id):
    user = g.user
    mood = request.json['mood']
    feels_meeting_goals = request.json['feels_meeting_goals']

    if mood is None or feels_meeting_goals is None:
        return jsonify({'error': 'JSON must contain mood and feels_meeting_goals'}), 400

    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.user_id == user_id).filter(DailySurveyResponses.date_submitted == date.today()).first())

    if survey is not None:
        return jsonify([{'error': 'User already submitted a daily survey for today. Edit using edit endpoint.'}]), 400
    else:
        new_survey = DailySurveyResponses()
        new_survey.user_id = user_id
        new_survey.mood = mood
        new_survey.feels_meeting_goals = feels_meeting_goals
        new_survey.date_created = date.today()
        db.session.add(new_survey)
        db.session.commit()

        return jsonify([{
            'daily_survey_id': new_survey.daily_survey_response_id,
            'mood': new_survey.mood,
            'feels_meeting_goals': new_survey.feels_meeting_goals,
            'date_created': new_survey.date_created
        }]), 201


@client_blueprint.route('/<user_id>/daily_survey/edit', methods=['PATCH'])
@require_auth
def edit_daily_survey(user_id):
    user = g.user
    survey_id = request.json['survey_id']
    mood = request.json['mood']
    feels_meeting_goals = request.json['feels_meeting_goals']

    survey = (db.session.query(DailySurveyResponses).filter(DailySurveyResponses.daily_survey_response_id == survey_id).first())

    if survey is None:
        return jsonify([{'error': 'Daily survey does not exist.'}]), 404
    elif survey.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to modify this content'}]), 401
    else:
        survey.mood = mood or survey.mood
        survey.feels_meeting_goals = feels_meeting_goals or survey.feels_meeting_goals

        return jsonify([{
            'daily_survey_id': survey.daily_survey_response_id,
            'mood': survey.mood,
            'feels_meeting_goals': survey.feels_meeting_goals
        }]), 200
