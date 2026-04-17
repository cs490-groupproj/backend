from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from models import *
from auth.authentication import require_auth
from auth.util import can_access_client_endpoint
from flask import Blueprint, jsonify, request, g

nutrition_blueprint = Blueprint('nutrition', __name__)

def _get_past_utc_bounds(tz_name, delta_days):
    try:
        local_tz = ZoneInfo(tz_name)
    except (ValueError, TypeError):
        return None, None

    now_local = datetime.now(local_tz)

    local_days_start = datetime.combine(
        now_local.date(),
        time.min,
        tzinfo=local_tz
    )

    local_days_end = local_days_start + timedelta(days=delta_days)

    return (
        local_days_start.astimezone(timezone.utc),
        local_days_end.astimezone(timezone.utc)
    )

@nutrition_blueprint.route('/plans/create', methods=['POST'])
@require_auth
def create_nutrition_plan():
    """
    Create meal plan
    ---
    tags:
        - Nutrition
    parameters:
        - name: body
          in: body
          required: true
          schema:
            required:
                - name
            properties:
                user_id:
                    type: string
                    required: true
                meal_type_id:
                    type: integer
                    required: true
                meal_datetime:
                    type: string
                    required: true
    responses:
        201:
            description: Created meal plan
            schema:
                type: object
                properties:
                    meal_plan_id:
                        type: integer
                    meal_type_id:
                        type: integer
                    meal_datetime:
                        type: string
                    eaten:
                        type: boolean
        400:
            description: Missing or invalid parameters
    """

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
        'eaten': new_plan.eaten,
    }), 201

@nutrition_blueprint.route('/plans/<meal_plan_id>')
@require_auth
def get_meal_plan(meal_plan_id):
    """
    Get meal plan
    ---
    tags:
        - Nutrition
    responses:
        200:
            description: Get meal plan
            schema:
                type: object
                properties:
                    meal_plan_id:
                        type: integer
                    meal_type_id:
                        type: integer
                    meal_datetime:
                        type: string
                    eaten:
                        type: boolean
                    meal_plan_foods:
                        type: array
                        items:
                            type: object
                            properties:
                                fdc_id:
                                    type: integer
                                food_name:
                                    type: string
                                calories:
                                    type: integer
                                servingSize:
                                    type: integer

        400:
            description: Missing or invalid parameters
    """

    meal_plan = (db.session.query(MealPlans).outerjoin(MealPlanFoods).filter(MealPlans.meal_plan_id == meal_plan_id).first())
    user_id = meal_plan.user_id

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to access this content'}), 401

    return jsonify({
        'meal_plan_id': meal_plan.meal_plan_id,
        'meal_type_id': meal_plan.meal_type_id,
        'eaten': meal_plan.eaten,
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
    """
    Add food to meal plan
    ---
    tags:
        - Nutrition
    parameters:
        - name: body
          in: body
          required: true
          schema:
            required:
                - name
            properties:
                fdc_id:
                    type: integer
                    required: true
                food_name:
                    type: string
                    required: true
                calories:
                    type: integer
                    required: true
                portion_size:
                    type: integer
                    required: true
    responses:
        201:
            description: Food added
            schema:
                type: object
                properties:
                    result:
                        type: string
        400:
            description: Missing or invalid parameters
    """
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


@nutrition_blueprint.route('/plans/<meal_plan_id>/remove_food', methods=['DELETE'])
@require_auth
def remove_food(meal_plan_id):
    """
    Remove food
    ---
    tags:
        - Nutrition
    parameters:
        - name: fdc_id
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Delete food item
            schema:
                type: object
                properties:
                    message:
                        type: string

        400:
            description: Missing or invalid parameters
    """
    meal_plan = db.session.query(MealPlans).filter(MealPlans.meal_plan_id == meal_plan_id).first()

    if not can_access_client_endpoint(g.user, meal_plan.user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    fdc_ic = request.args.get('fdc_id')

    if fdc_ic is None:
        return jsonify({'error': 'fdc_id is a required parameter'}), 400

    foods = meal_plan.meal_plan_foods

    for f in foods:
        if f.fdc_id == fdc_ic:
            db.session.delete(f)
            break

    db.session.commit()

    return jsonify({'message': 'Food removed'}), 200

@nutrition_blueprint.route('/plans/<meal_plan_id>/log_eaten', methods=['POST'])
@require_auth
def log_eaten(meal_plan_id):
    """
    Log eaten
    ---
    tags:
        - Nutrition
    responses:
        200:
            description: Logged as eaten
            schema:
                type: object
                properties:
                    meal_plan_id:
                        type: integer
                    logged_datetime:
                        type: string
    """

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


@nutrition_blueprint.route('/plans/<meal_plan_id>/unlog_eaten', methods=['POST'])
@require_auth
def unlog_plan(meal_plan_id):
    """
    Unlog eaten
    ---
    tags:
        - Nutrition
    responses:
        200:
            description: Unlogged as eaten
            schema:
                type: object
                properties:
                    message:
                        type: string
    """
    meal_plan = db.session.query(MealPlans).filter(MealPlans.meal_plan_id == meal_plan_id).first()

    if not can_access_client_endpoint(g.user, meal_plan.user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to modify this content'}), 401

    meal_plan.eaten = False
    meal_plan.logged_datetime = None

    db.session.commit()

    return jsonify({'message': 'Plan unlogged as eaten'}), 200


@nutrition_blueprint.route('/history')
@require_auth
def history():
    """
   Get meal plan history
    ---
    tags:
        - Nutrition
    parameters:
        - name: timezone
          in: path
          required: true
          type: string
        - name: user_id
          in: path
          required: true
          type: string
        - name: days
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get calories by day
            schema:
                type: array
                items:
                    type: object
                    properties:
                        date_submitted:
                            type: string
                        daily_total_calories:
                            type: number
        400:
            description: Missing or invalid parameters
    """
    timezone_string = request.args.get('timezone')
    user_id = request.args.get('user_id')
    days = request.args.get('days', default=7, type=int)

    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'user_id parameter is invalid'}), 400

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'error': 'You are not authorized to access this content'}), 401

    if timezone_string is None:
        return jsonify({'error': 'timezone_string parameter must be included in URL'}), 400

    if days is None or days < 1 or days > 366:
        return jsonify({'error': 'days must be an integer between 1 and 366'}), 400

    try:
        local_tz = ZoneInfo(timezone_string)
    except (ValueError, TypeError):
        return jsonify({'error': 'timezone_string parameter is not valid'}), 400

    now_local = datetime.now(local_tz)
    local_start_date = now_local.date() - timedelta(days=days - 1)
    local_start_dt = datetime.combine(local_start_date, time.min, tzinfo=local_tz)
    local_end_dt = datetime.combine(now_local.date() + timedelta(days=1), time.min, tzinfo=local_tz)

    utc_start = local_start_dt.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end_dt.astimezone(timezone.utc).replace(tzinfo=None)

    meal_plans = (
        db.session.query(MealPlans)
        .filter(MealPlans.user_id == user_id)
        .filter(MealPlans.logged_datetime >= utc_start, MealPlans.logged_datetime < utc_end)
        .all()
    )

    totals_by_local_day = {}
    for offset in range(days):
        d = local_start_date + timedelta(days=offset)
        totals_by_local_day[d.isoformat()] = 0

    for mp in meal_plans:
        logged_dt = getattr(mp, 'logged_datetime', None)
        if logged_dt is None:
            continue

        local_day_key = logged_dt.replace(tzinfo=timezone.utc).astimezone(local_tz).date().isoformat()
        if local_day_key not in totals_by_local_day:
            continue

        for mpf in mp.meal_plan_foods:
            calories = float(getattr(mpf, 'calories', 0) or 0)
            serving_size = float(getattr(mpf, 'serving_size', 0) or 0)
            totals_by_local_day[local_day_key] += calories * (serving_size / 100.0)

    return jsonify([
        {
            'date_submitted': day_key,
            'daily_total_calories': round(total_cals, 2),
        }
        for day_key, total_cals in totals_by_local_day.items()
    ]), 200



@nutrition_blueprint.route('/today')
@require_auth
def today():
    """
   Get today's meal plans
    ---
    tags:
        - Nutrition
    parameters:
        - name: timezone
          in: path
          required: true
          type: string
        - name: user_id
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get meal plans by day
            schema:
                type: object
                properties:
                    meal_plans:
                        type: array
                        items:
                            type: object
                            properties:
                                meal_plan_id:
                                    type: integer
                                meal_type:
                                    type: integer
                                meal_plan_foods:
                                    type: array
                                    items:
                                        type: object
                                        properties:
                                            fdc_id:
                                                type: integer
                                            food_name:
                                                type: string
                                            calories:
                                                type: integer
                                            portion_size:
                                                type: integer
                    daily_total_calories:
                        type: integer
        400:
            description: Missing or invalid parameters
    """
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

    tz_start, tz_end = _get_past_utc_bounds(timezone_string, 1)

    if tz_start is None or tz_end is None:
        return jsonify({'error': 'timezone_string parameter is not valid'}), 400

    tz_start = tz_start.replace(tzinfo=None)
    tz_end = tz_end.replace(tzinfo=None)

    meal_plans = db.session.query(MealPlans).filter(MealPlans.user_id == user_id).filter(MealPlans.logged_datetime >= tz_start, MealPlans.logged_datetime < tz_end).all()

    total_cals = 0
    for mp in meal_plans:
        for mpf in mp.meal_plan_foods:
            portion_size = mpf.serving_size
            total_cals += mpf.calories * (portion_size // 100)

    return jsonify({
        'meal_plans': [{
            'meal_plan_id': mp.meal_plan_id,
            'meal_type': mp.meal_type_id,
            'meal_plan_foods': [{
                'fdc_id': f.fdc_id,
                'food_name': f.food_name,
                'calories': f.calories,
                'portion_size': f.serving_size,
            } for f in mp.meal_plan_foods]
        } for mp in meal_plans],
        'daily_total_calories': total_cals
    })

@nutrition_blueprint.route('/plans/plans_by_user')
@require_auth
def plans_by_user():
    """
    Get meal plans by user
    ---
    tags:
        - Nutrition
    parameters:
        - name: user_id
          in: path
          required: true
          type: string
    responses:
        200:
            description: Get meal plans by day
            schema:
                type: object
                properties:
                    meal_plans:
                        type: array
                        items:
                            type: object
                            properties:
                                meal_plan_id:
                                    type: integer
                                meal_plan_foods:
                                    type: array
                                    items:
                                        type: object
                                        properties:
                                            fdc_id:
                                                type: integer
        400:
            description: Missing or invalid parameters
    """
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