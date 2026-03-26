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
        'weight_goal': current_goals.weight_goal,
        'height_goal': current_goals.height_goal,
        'exercise_minutes_goal': current_goals.exercise_minutes_goal,
        'personal_goals': current_goals.personal_goals,
        'date_created': current_goals.date_created
    }), 200

@client_blueprint.route('/<user_id>/edit_goals')
@require_auth
def edit_goals(user_id):
    user = g.user

    old_goal = (db.session.query(ClientGoals).filter(ClientGoals.user_id == user_id).order_by(ClientGoals.date_created.desc()).first())
    new_goal = ClientGoals()
    new_goal.user_id = user.user_id

    if old_goal.user_id != user.user_id:
        return jsonify([{'error': 'You are not authorized to modify this content'}]), 401

    if (new_weight := request.json['weight']) is not None:
        new_goal.weight_goal = new_weight
    else:
        new_goal.weight_goal = old_goal.weight_goal

    if (new_height := request.json['height']) is not None:
        new_goal.height_goal = new_height
    else:
        new_goal.height_goal = old_goal.height_goal

    if (new_exercise_minutes := request.json['exercise_minutes']) is not None:
        new_goal.exercise_minutes_goal = new_exercise_minutes

    if (new_personal_goals := request.json['personal_goals']) is not None:
        new_goal.personal_goals = new_personal_goals
    else:
        new_goal.personal_goals = old_goal.personal_goals

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'weight_goal': new_goal.weight_goal,
        'height_goal': new_goal.height_goal,
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
        'weight_goal': g.weight_goal,
        'height_goal': g.height_goal,
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
