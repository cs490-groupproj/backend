from enum import Enum
from uuid import UUID

from models import *
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g
from datetime import date

client_blueprint = Blueprint('client_blueprint', __name__)

@client_blueprint.route('/<user_id>/current_goals')
@require_auth
def get_current_goals(user_id):
    user = g.user
    current_goals = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).first())

    if current_goals.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to view this content'}]), 401

    return jsonify({
        'primary_goal_id': current_goals.primary_goal,
        'weight_goal': current_goals.weight_goal,
        'exercise_minutes_goal': current_goals.exercise_minutes_goal,
        'personal_goals': current_goals.personal_goals,
        'date_created': current_goals.date_created
    }), 200

class PrimaryGoals(Enum):
    LOSE_WEIGHT = 0
    BUILD_MUSCLE = 1
    INCREASE_STRENGTH = 2
    IMPROVE_ENDURANCE = 3
    GENERAL_FITNESS = 4
    SPORTS_PERFORMANCE = 5

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

    if (new_primary_goal := request.json.get('primary_goal')) is not None:
        if new_primary_goal not in PrimaryGoals:
            return jsonify([{
                'error': 'Primary goal is not valid. Use the primary goal ID to refer to your goal.',
                'type_hints': {
                    PrimaryGoals.LOSE_WEIGHT.value: 'LOSE_WEIGHT',
                    PrimaryGoals.BUILD_MUSCLE.value: 'BUILD_MUSCLE',
                    PrimaryGoals.INCREASE_STRENGTH.value: 'INCREASE_STRENGTH',
                    PrimaryGoals.IMPROVE_ENDURANCE.value: 'IMPROVE_ENDURE',
                    PrimaryGoals.GENERAL_FITNESS.value: 'GENERAL_FITNESS',
                    PrimaryGoals.SPORTS_PERFORMANCE.value: 'SPORTS_PERFORMANCE'
                }
            }]), 401
        else:
            new_goal.primary_goal = new_primary_goal

    if (new_weight := request.json.get('weight')) is not None:
        new_goal.weight_goal = new_weight
    if (new_exercise_minutes := request.json.get('exercise_minutes')) is not None:
        new_goal.exercise_minutes_goal = new_exercise_minutes
    if (new_personal_goals := request.json.get('personal_goals')) is not None:
        new_goal.personal_goals = new_personal_goals

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'primary_goal_id': new_goal.primary_goal,
        'weight_goal': new_goal.weight_goal,
        'exercise_minutes_goal': new_goal.exercise_minutes_goal,
        'personal_goals': new_goal.personal_goals,
        'date_created': new_goal.date_created
    }), 200


@client_blueprint.route('/<user_id>/edit_goals')
@require_auth
def edit_goals(user_id):
    user = g.user

    old_goal = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).first())
    new_goal = ClientGoals()
    new_goal.user_id = UUID(user_id)

    if old_goal.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to modify this content'}]), 401

    if (new_primary_goal := request.json.get('primary_goal')) is not None:
        if new_primary_goal not in PrimaryGoals:
            return jsonify([{
                'error': 'Primary goal is not valid. Use the primary goal ID to refer to your goal.',
                'type_hints': {
                    PrimaryGoals.LOSE_WEIGHT: 'LOSE_WEIGHT',
                    PrimaryGoals.BUILD_MUSCLE: 'BUILD_MUSCLE',
                    PrimaryGoals.INCREASE_STRENGTH: 'INCREASE_STRENGTH',
                    PrimaryGoals.IMPROVE_ENDURANCE: 'IMPROVE_ENDURE',
                    PrimaryGoals.GENERAL_FITNESS: 'GENERAL_FITNESS',
                    PrimaryGoals.SPORTS_PERFORMANCE: 'SPORTS_PERFORMANCE'
                }
            }]), 401
        else:
            new_goal.primary_goal = new_primary_goal
    else:
        new_primary_goal.primary_goal = old_goal.primary_goal

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
        'primary_goal_id': new_goal.primary_goal,
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
        'primary_goal_id': g.primary_goal,
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

@client_blueprint.route('/<user_id>/daily_survey/edit', methods=['POST'])
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
