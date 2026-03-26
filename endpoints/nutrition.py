from models import *
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g

nutrition_blueprint = Blueprint('nutrition', __name__)

@nutrition_blueprint.route('/plans/create', methods=['POST'])
@require_auth
def create_nutrition_plan():
    user = g.user
    new_plan = MealPlans()
    new_plan.user_id = user.user_id
    db.session.add(new_plan)
    db.session.commit()

    return jsonify({
        'meal_plan_id': new_plan.meal_plan_id,
    }), 201

@nutrition_blueprint.route('/plans/<meal_plan_id>')
@require_auth
def get_meal_plan(meal_plan_id):
    user = g.user
    meal_plan = (db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    if meal_plan.user_id != user.user_id:
        return jsonify({'error': 'You are not authorized to view this content'}), 401
    else:
        return jsonify({
            'meal_plan_id': meal_plan.meal_plan_id,
            'meal_plan_foods': [
                {'fdcId': f.fdc_id} for f in meal_plan.meal_plan_foods
            ]
        }), 200

@nutrition_blueprint.route('/plans/<meal_plan_id>/add_food', methods=['POST'])
@require_auth
def add_food(meal_plan_id):
    user = g.user
    meal_plan = (
        db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    if meal_plan.user_id != user.user_id:
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal_plan_foods = MealPlanFoods()
    meal_plan_foods.meal_plan_id = meal_plan_id
    meal_plan_foods.meal_type = request.json['meal_type_id']
    meal_plan_foods.fdc_id = request.json['fdc_id']
    db.session.add(meal_plan_foods)
    db.session.commit()

    return jsonify({'result': 'Food added'}), 201

@nutrition_blueprint.route('/plans/<meal_plan_id>/log_eaten', methods=['POST'])
@require_auth
def log_eaten(meal_plan_id):
    user = g.user
    meal_datetime = request.json['meal_date']
    meal_plan = (db.session.query(MealPlans).filter(MealPlans.meal_plan_id == meal_plan_id).first())

    if meal_plan.user_id != user.user_id:
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal = Meals()
    meal.user_id = user.user_id
    meal.meal_datetime = meal_plan.meal_datetime
    meal.meal_type = meal_plan.meal_type
    db.session.add(meal)
    db.session.commit()

    return jsonify({
        'meal_id': meal.meal_id,
    }), 200


@nutrition_blueprint.route('/plans/plans_by_user')
@require_auth
def plans_by_user():
    user_id = request.args.get('user_id')

    if user_id is None:
        return jsonify({'error': 'user_id parameter must be included in URL'}), 400

    user = g.user
    meal_plans = (db.session.query(MealPlans).filter(MealPlans.user_id == user.user_id).all())

    return jsonify({
        'meal_plans': [{
            'meal_plan_id': mp.meal_plan_id,
            'meal_plan_foods': [{
                'fdc_id': f.fdc_id
            } for f in mp.meal_plan_foods]
        } for mp in meal_plans]
    })