from datetime import datetime
from uuid import UUID

from models import *
from auth.authentication import require_auth
from auth.util import can_access_client_endpoint
from flask import Blueprint, jsonify, request, g

nutrition_blueprint = Blueprint('nutrition', __name__)

@nutrition_blueprint.route('/plans/create', methods=['POST'])
@require_auth
def create_nutrition_plan():

    user_id = request.json.get('user_id')
    meal_type_id = request.json.get('meal_type_id')
    meal_datetime = request.json.get('meal_datetime')

    if user_id is None or meal_type_id is None or meal_datetime is None:
        return jsonify({'error': 'user_id and meal_type_id parameters must be included in request body'}), 400
    else:
        user_id = UUID(user_id)

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    try:
        meal_datetime = datetime.fromisoformat(meal_datetime)
    except (ValueError, AttributeError):
        return jsonify({'error': 'Invalid datetime format'}), 400

    try:
        int(meal_type_id)
        if meal_type_id < 1 or meal_type_id > 4:
            raise ValueError
    except ValueError:
        return jsonify({
            'error': 'meal_type_id parameter must be an integer 1-4',
            'guide': {
                1: 'Breakfast',
                2: 'Lunch',
                3: 'Dinner',
                4: 'Snack'
            }
        }), 400

    new_plan = MealPlans()
    new_plan.user_id = user_id
    new_plan.meal_type_id = meal_type_id
    new_plan.meal_datetime = meal_datetime
    db.session.add(new_plan)
    db.session.commit()

    return jsonify({
        'meal_plan_id': new_plan.meal_plan_id,
    }), 201

@nutrition_blueprint.route('/plans/<meal_plan_id>')
@require_auth
def get_meal_plan(meal_plan_id):

    meal_plan = (db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    user_id = meal_plan.user_id

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to access this content'}), 401

    return jsonify({
        'meal_plan_id': meal_plan.meal_plan_id,
        'meal_type_id': meal_plan.meal_type_id,
        'meal_plan_foods': [
            {'fdcId': f.fdc_id} for f in meal_plan.meal_plan_foods
        ]
    }), 200

@nutrition_blueprint.route('/plans/<meal_plan_id>/add_food', methods=['POST'])
@require_auth
def add_food(meal_plan_id):

    meal_plan = (db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    user_id = meal_plan.user_id

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal_plan_foods = MealPlanFoods()
    meal_plan_foods.meal_plan_id = meal_plan_id
    meal_plan_foods.fdc_id = request.json['fdc_id']
    db.session.add(meal_plan_foods)
    db.session.commit()

    return jsonify({'result': 'Food added'}), 201

@nutrition_blueprint.route('/plans/<meal_plan_id>/log_eaten', methods=['POST'])
@require_auth
def log_eaten(meal_plan_id):

    meal_plan = (db.session.query(MealPlans).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    user_id = meal_plan.user_id


    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal_plan.eaten = True

    db.session.commit()

    return jsonify({
        'meal_plan_id': meal_plan.meal_plan_id,
    }), 200


@nutrition_blueprint.route('/plans/plans_by_user')
@require_auth
def plans_by_user():
    user_id = request.args.get('user_id')

    if user_id is None:
        return jsonify({'error': 'user_id parameter must be included in URL'}), 400
    else:
        user_id = UUID(user_id)

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to access this content'}), 401

    meal_plans = (db.session.query(MealPlans).filter(MealPlans.user_id == user_id).all())

    return jsonify({
        'meal_plans': [{
            'meal_plan_id': mp.meal_plan_id,
            'meal_plan_foods': [{
                'fdc_id': f.fdc_id
            } for f in mp.meal_plan_foods]
        } for mp in meal_plans]
    })