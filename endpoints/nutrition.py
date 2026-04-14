from datetime import datetime, date, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from models import *
from auth.authentication import require_auth
from auth.util import can_access_client_endpoint
from flask import Blueprint, jsonify, request, g

nutrition_blueprint = Blueprint('nutrition', __name__)

def _get_utc_day_bounds(tz_name):
    try:
        local_tz = ZoneInfo(tz_name)
    except (ValueError, TypeError):
        return None, None

    now_local = datetime.now(local_tz)

    local_day_start = datetime.combine(
        now_local.date(),
        time.min,
        tzinfo=local_tz
    )

    local_day_end = local_day_start + timedelta(days=1)

    return (
        local_day_start.astimezone(timezone.utc),
        local_day_end.astimezone(timezone.utc)
    )

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
    new_plan.eaten = False
    new_plan.meal_datetime = meal_datetime
    db.session.add(new_plan)
    db.session.commit()

    return jsonify({
        'meal_plan_id': new_plan.meal_plan_id,
        'meal_type_id': new_plan.meal_type_id,
        'meal_datetime': str(new_plan.meal_datetime),
        'eaten': str(new_plan.eaten).lower(),
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
            {
                'fdcId': f.fdc_id,
                'foodName': f.food_name,
                'calories': f.calories,
                'servingSize': f.serving_size,
            } for f in meal_plan.meal_plan_foods
        ]
    }), 200

@nutrition_blueprint.route('/plans/<meal_plan_id>/add_food', methods=['POST'])
@require_auth
def add_food(meal_plan_id):

    meal_plan = (db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    user_id = meal_plan.user_id

    fdc_id = request.json.get('fdc_id')
    food_name = request.json.get('food_name')
    calories = request.json.get('calories')
    portion_size = request.json.get('portion_size')

    if fdc_id is None or food_name is None or calories is None:
        return jsonify({'error': 'fdc_id, food_name, calories, and portion_size parameters must be included in URL'}), 400

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal_plan_foods = MealPlanFoods()
    meal_plan_foods.meal_plan_id = meal_plan_id
    meal_plan_foods.fdc_id = fdc_id
    meal_plan_foods.food_name = food_name
    meal_plan_foods.calories = calories
    meal_plan_foods.serving_size = portion_size
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
    meal_plan.logged_datetime = datetime.now(tz=timezone.utc)

    db.session.commit()

    return jsonify({
        'meal_plan_id': meal_plan.meal_plan_id,
        'logged_datetime': str(meal_plan.logged_datetime.isoformat()),
    }), 200

@nutrition_blueprint.route('today')
@require_auth
def today():
    timezone_string = request.args.get('timezone')
    user_id = request.args.get('user_id')

    try:
        user_id = UUID(user_id)
    except ValueError:
        return jsonify({'error': 'user_id parameter is invalid'}), 400

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to access this content'}), 401

    if timezone_string is None:
        return jsonify({'error': 'timezone_string parameter must be included in URL'}), 400

    tz_start, tz_end = _get_utc_day_bounds(timezone_string)

    if tz_start is None or tz_end is None:
        return jsonify({'error': 'timezone_string parameter is not valid'}), 400

    tz_start = tz_start.replace(tzinfo=None)
    tz_end = tz_end.replace(tzinfo=None)

    meal_plans = db.session.query(MealPlans).filter(MealPlans.user_id == user_id).filter(MealPlans.logged_datetime >= tz_start, MealPlans.logged_datetime < tz_end).all()

    total_cals = 0
    for mp in meal_plans:
        for mpf in mp.meal_plan_foods:
            portion_size = mpf.portion_size
            total_cals += mpf.calories * (portion_size // 100)

    return jsonify({
        'meal_plans': [{
            'meal_plan_id': mp.meal_plan_id,
            'meal_type': mp.meal_type,
            'meal_plan_foods': [{
                'fdc_id': f.fdc_id,
                'food_name': f.food_name,
                'calories': f.calories,
                'portion_size': f.portion_size,
            } for f in mp.meal_plan_foods]
        } for mp in meal_plans],
        'daily_total_calories': total_cals
    })


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