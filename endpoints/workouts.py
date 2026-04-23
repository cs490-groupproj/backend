from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from auth.authentication import require_auth
from models import (
    BodyParts,
    ExerciseCategories,
    Exercises,
    WorkoutExercises,
    WorkoutPlanDays,
    WorkoutPlanExercises,
    WorkoutPlans,
    Workouts,
    WorkoutTypes,
    db,
)

workouts_blueprint = Blueprint('workouts_blueprint', __name__)


def _parse_uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _num_or_none(v):
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        return v
    if isinstance(v, str) and v.strip() == '':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int_or_none(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _decimal_or_none(v):
    n = _num_or_none(v)
    if n is None:
        return None
    return Decimal(str(n))


def _serialize_decimal(val):
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return val


def _parse_datetime_or_none(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None
    if raw.endswith('Z'):
        raw = raw[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _serialize_datetime(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _parse_time_or_none(value):
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return time.fromisoformat(raw)
    except ValueError:
        return None


def _serialize_time(val):
    if val is None:
        return None
    if isinstance(val, time):
        return val.isoformat()
    return str(val)


def _require_authorized_user_id():
    uid_raw = request.args.get('user_id')
    uid = _parse_uuid(uid_raw)
    if uid is None:
        return None, (jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400)
    if uid != g.user.user_id:
        return None, (jsonify({'error': 'You can only list your own workouts'}), 403)
    return uid, None


def _validated_days_param():
    days = request.args.get('days', default=7, type=int)
    if days is None or days < 1 or days > 366:
        return None, (jsonify({'error': 'days must be an integer between 1 and 366'}), 400)
    return days, None


def _workout_exercise_public(we: WorkoutExercises):
    ex = we.exercise
    return {
        'workout_exercise_id': we.workout_exercise_id,
        'workout_id': we.workout_id,
        'exercise_id': we.exercise_id,
        'name': ex.name if ex else None,
        'exercise_youtube_url': ex.youtube_url if ex else None,
        'position': we.position,
        'sets': we.sets,
        'reps': we.reps,
        'weight': _serialize_decimal(we.weight),
        'rpe': _serialize_decimal(we.rpe),
        'duration_sec': we.duration_sec,
        'distance_m': _serialize_decimal(we.distance_m),
        'pace_sec_per_km': _serialize_decimal(we.pace_sec_per_km),
        'calories': we.calories,
        'notes': we.notes,
    }


def _plan_exercise_public(pe: WorkoutPlanExercises):
    ex = pe.exercise
    return {
        'workout_plan_exercise_id': pe.workout_plan_exercise_id,
        'workout_plan_id': pe.workout_plan_id,
        'exercise_id': pe.exercise_id,
        'name': ex.name if ex else None,
        'position': pe.position,
        'sets': pe.sets,
        'reps': pe.reps,
        'weight': _serialize_decimal(pe.weight),
        'rpe': _serialize_decimal(pe.rpe),
        'duration_sec': pe.duration_sec,
        'distance_m': _serialize_decimal(pe.distance_m),
        'pace_sec_per_km': _serialize_decimal(pe.pace_sec_per_km),
        'calories': pe.calories,
        'notes': pe.notes,
    }


def _plan_day_public(day: WorkoutPlanDays):
    return {
        'id': day.id,
        'workout_plan_id': day.workout_plan_id,
        'weekday': day.weekday,
        'schedule_time': _serialize_time(day.schedule_time),
    }


def _get_workout_for_user(workout_id: int, user_id):
    return (
        db.session.query(Workouts)
        .options(joinedload(Workouts.workout_exercises).joinedload(WorkoutExercises.exercise))
        .filter(Workouts.workout_id == workout_id, Workouts.user_id == user_id)
        .first()
    )


def _apply_workout_exercise_fields(row: WorkoutExercises, data: dict):
    if 'exercise_id' in data:
        row.exercise_id = data['exercise_id']
    if 'position' in data:
        row.position = _int_or_none(data['position']) if data['position'] is not None else 0
    if 'sets' in data:
        row.sets = _int_or_none(data['sets'])
    if 'reps' in data:
        row.reps = _int_or_none(data['reps'])
    if 'weight' in data:
        row.weight = _decimal_or_none(data['weight'])
    if 'rpe' in data:
        row.rpe = _decimal_or_none(data['rpe'])
    if 'duration_sec' in data:
        row.duration_sec = _int_or_none(data['duration_sec'])
    if 'distance_m' in data:
        row.distance_m = _decimal_or_none(data['distance_m'])
    if 'pace_sec_per_km' in data:
        row.pace_sec_per_km = _decimal_or_none(data['pace_sec_per_km'])
    if 'calories' in data:
        row.calories = _int_or_none(data['calories'])
    if 'notes' in data:
        row.notes = data['notes']


def _apply_plan_exercise_fields(row: WorkoutPlanExercises, data: dict):
    if 'exercise_id' in data:
        row.exercise_id = data['exercise_id']
    if 'position' in data:
        row.position = _int_or_none(data['position']) if data['position'] is not None else 0
    if 'sets' in data:
        row.sets = _int_or_none(data['sets'])
    if 'reps' in data:
        row.reps = _int_or_none(data['reps'])
    if 'weight' in data:
        row.weight = _decimal_or_none(data['weight'])
    if 'rpe' in data:
        row.rpe = _decimal_or_none(data['rpe'])
    if 'duration_sec' in data:
        row.duration_sec = _int_or_none(data['duration_sec'])
    if 'distance_m' in data:
        row.distance_m = _decimal_or_none(data['distance_m'])
    if 'pace_sec_per_km' in data:
        row.pace_sec_per_km = _decimal_or_none(data['pace_sec_per_km'])
    if 'calories' in data:
        row.calories = _int_or_none(data['calories'])
    if 'notes' in data:
        row.notes = data['notes']


def _exercise_exists(exercise_id: int) -> bool:
    return db.session.query(Exercises.exercise_id).filter(Exercises.exercise_id == exercise_id).first() is not None


# --- Lookup tables ---


@workouts_blueprint.route('/exercise-categories', methods=['GET'])
@require_auth
def list_exercise_categories():
    """
    List exercise categories
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get exercise categories
            schema:
                type: array
                items:
                    type: object
                    properties:
                        category_id:
                            type: integer
                        name:
                            type: string
    """
    rows = db.session.query(ExerciseCategories).order_by(ExerciseCategories.name).all()
    return jsonify([{'category_id': r.category_id, 'name': r.name} for r in rows]), 200


@workouts_blueprint.route('/body-parts', methods=['GET'])
@require_auth
def list_body_parts():
    """
    List body parts
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get body parts
            schema:
                type: array
                items:
                    type: object
                    properties:
                        body_part_id:
                            type: integer
                        name:
                            type: string

    """
    rows = db.session.query(BodyParts).order_by(BodyParts.name).all()
    return jsonify([{'body_part_id': r.body_part_id, 'name': r.name} for r in rows]), 200


@workouts_blueprint.route('/workout-types', methods=['GET'])
@require_auth
def list_workout_types():
    """
    List workout types
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get workout types
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_type_id:
                            type: integer
                        name:
                            type: string

    """
    rows = db.session.query(WorkoutTypes).order_by(WorkoutTypes.name).all()
    response = [{'workout_type_id': r.workout_type_id, 'name': r.name} for r in rows]
    print(f"[WORKOUTS DEBUG] GET /workout-types response: {response}")
    return jsonify(response), 200


# --- Master exercises ---


@workouts_blueprint.route('/exercises', methods=['GET'])
@require_auth
def list_exercises():
    """
    List exercises
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get exercise categories
            schema:
                type: array
                items:
                    type: object
                    properties:
                        exercise_id:
                            type: integer
                        name:
                            type: string
                        youtube_url:
                            type: string
                        body_part_id:
                            type: integer
                        category_id:
                            type: integer
                        body_part:
                            type: string
                        category:
                            type: string

    """
    rows = (
        db.session.query(Exercises)
        .options(joinedload(Exercises.body_part), joinedload(Exercises.category))
        .order_by(Exercises.name)
        .all()
    )
    out = []
    for e in rows:
        out.append({
            'exercise_id': e.exercise_id,
            'name': e.name,
            'youtube_url': e.youtube_url,
            'body_part_id': e.body_part_id,
            'category_id': e.category_id,
            'body_part': e.body_part.name if e.body_part else None,
            'category': e.category.name if e.category else None,
        })
    print(f"[WORKOUTS DEBUG] GET /exercises response: {out}")
    return jsonify(out), 200


@workouts_blueprint.route('/exercises/<int:exercise_id>', methods=['GET'])
@require_auth
def get_exercise(exercise_id):
    """
    Get exercise
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get exercise
            schema:
                type: object
                properties:
                    exercise_id:
                        type: integer
                    name:
                        type: string
                    youtube_url:
                        type: string
                    body_part_id:
                        type: integer
                    category_id:
                        type: integer
                    body_part:
                        type: string
                    category:
                        type: string

        404:
            description: Exercise not found

    """
    e = (
        db.session.query(Exercises)
        .options(joinedload(Exercises.body_part), joinedload(Exercises.category))
        .filter(Exercises.exercise_id == exercise_id)
        .first()
    )
    if e is None:
        return jsonify({'error': 'Exercise not found'}), 404
    return jsonify({
        'exercise_id': e.exercise_id,
        'name': e.name,
        'youtube_url': e.youtube_url,
        'body_part_id': e.body_part_id,
        'category_id': e.category_id,
        'body_part': e.body_part.name if e.body_part else None,
        'category': e.category.name if e.category else None,
    }), 200


# --- Workout plans (templates) ---


@workouts_blueprint.route('/workout-plans', methods=['GET'])
@require_auth
def list_workout_plans():
    """
    List workout plans
    ---
    tags:
        - Workouts
    parameters:
        - name: created_by
          in: path
          type: string
          required: true
    responses:
        200:
            description: Get workout plans
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_plan_id:
                            type: integer
                        title:
                            type: string
                        created_by:
                            type: string
                        duration_min:
                            type: integer
        400:
            description: Invalid parameters

    """
    created_by_raw = request.args.get('created_by')
    q = db.session.query(WorkoutPlans)
    if created_by_raw:
        if created_by_raw.strip().lower() == 'me':
            q = q.filter(WorkoutPlans.created_by == g.user.user_id)
        else:
            created_by_uuid = _parse_uuid(created_by_raw)
            if created_by_uuid is None:
                return jsonify({'error': 'created_by must be a valid UUID or "me"'}), 400
            q = q.filter(WorkoutPlans.created_by == created_by_uuid)

    rows = q.order_by(WorkoutPlans.title).all()
    return jsonify([
        {
            'workout_plan_id': r.workout_plan_id,
            'title': r.title,
            'created_by': str(r.created_by) if r.created_by else None,
            'duration_min': r.duration_min,
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workout-plans/<int:plan_id>', methods=['GET'])
@require_auth
def get_workout_plan(plan_id):
    """
    Get workout plan
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Get workout plan
            schema:
                type: object
                properties:
                    workout_plan_id:
                        type: integer
                    title:
                        type: string
                    workout_type_id:
                        type: integer
                    description:
                        type: string
                    created_by:
                        type: string
                    duration_min:
                        type: integer
                    assignments:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                workout_plan_id:
                                    type: integer
                                weekday:
                                    type: string
                                schedule_time:
                                    type: string
                    exercises:
                        type: array
                        items:
                            type: object
                            properties:
                                workout_plan_exercise_id:
                                    type: integer
                                workout_plan_id:
                                    type: integer
                                exercise_id:
                                    type: integer
                                name:
                                    type: string
                                position:
                                    type: integer
                                sets:
                                    type: integer
                                reps:
                                    type: integer
                                weight:
                                    type: number
                                rpe:
                                    type: number
                                duration_sec:
                                    type: integer
                                distance_m:
                                    type: number
                                pace_sec_per_km:
                                    type: number
                                calories:
                                    type: integer
                                notes:
                                    type: string

        404:
            description: Workout plan not found

    """
    plan = (
        db.session.query(WorkoutPlans)
        .options(
            joinedload(WorkoutPlans.workout_plan_exercises).joinedload(WorkoutPlanExercises.exercise),
            joinedload(WorkoutPlans.workout_plan_days),
        )
        .filter(WorkoutPlans.workout_plan_id == plan_id)
        .first()
    )
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404
    exercises = sorted(plan.workout_plan_exercises, key=lambda x: (x.position, x.workout_plan_exercise_id))
    return jsonify({
        'workout_plan_id': plan.workout_plan_id,
        'title': plan.title,
        'workout_type_id': plan.workout_type_id,
        'description': plan.description,
        'created_by': str(plan.created_by) if plan.created_by else None,
        'duration_min': plan.duration_min,
        'assignments': [_plan_day_public(day) for day in sorted(plan.workout_plan_days, key=lambda d: d.id)],
        'exercises': [_plan_exercise_public(pe) for pe in exercises],
    }), 200


@workouts_blueprint.route('/workout-plans', methods=['POST'])
@require_auth
def create_workout_plan():
    """
    Create workout plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                title:
                    type: string
                workout_type_id:
                    type: integer
                description:
                    type: string
                duration_min:
                    type: integer
                created_by:
                    type: string
    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    workout_plan_id:
                        type: integer
        400:
            description: Invalid parameters

    """
    body = request.get_json(silent=True) or {}
    title = body.get('title')
    if not title or not str(title).strip():
        return jsonify({'error': 'title is required'}), 400

    plan = WorkoutPlans()
    plan.title = str(title).strip()
    plan.workout_type_id = _int_or_none(body.get('workout_type_id'))
    plan.description = body.get('description')
    plan.duration_min = _int_or_none(body.get('duration_min'))
    created_by = body.get('created_by')
    if created_by is not None:
        uid = _parse_uuid(created_by)
        if uid is None:
            return jsonify({'error': 'Invalid created_by user id'}), 400
        plan.created_by = uid
    else:
        plan.created_by = g.user.user_id

    if plan.workout_type_id is not None:
        if db.session.query(WorkoutTypes).filter(WorkoutTypes.workout_type_id == plan.workout_type_id).first() is None:
            return jsonify({'error': 'Invalid workout_type_id'}), 400

    db.session.add(plan)
    db.session.commit()
    return jsonify({'workout_plan_id': plan.workout_plan_id}), 201


@workouts_blueprint.route('/workout-plans/<int:plan_id>', methods=['PATCH'])
@require_auth
def update_workout_plan(plan_id):
    """
    Update workout plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                title:
                    type: string
                workout_type_id:
                    type: integer
                description:
                    type: string
                duration_min:
                    type: integer
                created_by:
                    type: string
    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    plan = db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == plan_id).first()
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({'error': 'JSON body required'}), 400

    if 'title' in body:
        title = body.get('title')
        if not title or not str(title).strip():
            return jsonify({'error': 'title cannot be empty'}), 400
        plan.title = str(title).strip()

    if 'workout_type_id' in body:
        workout_type_id = _int_or_none(body.get('workout_type_id'))
        if workout_type_id is not None:
            if db.session.query(WorkoutTypes).filter(WorkoutTypes.workout_type_id == workout_type_id).first() is None:
                return jsonify({'error': 'Invalid workout_type_id'}), 400
        plan.workout_type_id = workout_type_id

    if 'description' in body:
        plan.description = body.get('description')

    if 'duration_min' in body:
        plan.duration_min = _int_or_none(body.get('duration_min'))

    if 'created_by' in body:
        created_by = body.get('created_by')
        if created_by is None:
            plan.created_by = None
        else:
            uid = _parse_uuid(created_by)
            if uid is None:
                return jsonify({'error': 'Invalid created_by user id'}), 400
            plan.created_by = uid

    db.session.commit()
    return jsonify({'message': 'Workout plan updated'}), 200


@workouts_blueprint.route('/workout-plans/<int:plan_id>/exercises', methods=['POST'])
@require_auth
def add_plan_exercises(plan_id):
    """
    Add exercise to workout plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                exercises:
                    type: array
                    items:
                        type: object
                        properties:
                            exercise_id:
                                type: integer
                            position:
                                type: integer
    responses:
        200:
            description: Get workout plan exercises
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    plan = db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == plan_id).first()
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    body = request.get_json(silent=True) or {}
    items = body.get('exercises')
    if items is None:
        items = [body]
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Send a single exercise object or { "exercises": [ ... ] }'}), 400

    for item in items:
        eid = _int_or_none(item.get('exercise_id'))
        if eid is None or not _exercise_exists(eid):
            return jsonify({'error': f'Invalid exercise_id: {item.get("exercise_id")}'}), 400
        row = WorkoutPlanExercises()
        row.workout_plan_id = plan_id
        row.exercise_id = eid
        row.position = _int_or_none(item.get('position')) if item.get('position') is not None else 0
        _apply_plan_exercise_fields(row, {k: v for k, v in item.items() if k != 'exercise_id'})
        db.session.add(row)

    db.session.commit()
    return jsonify({'message': 'Added'}), 201


@workouts_blueprint.route('/workout-plans/<int:plan_id>/assignments', methods=['POST'])
@require_auth
def add_plan_assignments(plan_id):
    """
    Update workout plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                assignments:
                    type: array
                    items:
                        type: object
                        properties:
                            weekday:
                                type: string
                            schedule_time:
                                type: string
    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    assignments:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                workout_plan_id:
                                    type: integer
                                weekday:
                                    type: string
                                schedule_time:
                                    type: string

        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    plan = db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == plan_id).first()
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    body = request.get_json(silent=True) or {}
    items = body.get('assignments')
    if items is None:
        items = [body]
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Send a single assignment object or { "assignments": [ ... ] }'}), 400

    created = []
    for item in items:
        weekday = item.get('weekday')
        if not isinstance(weekday, str) or not weekday.strip():
            return jsonify({'error': 'weekday must be a non-empty string'}), 400
        weekday = weekday.strip()
        if len(weekday) > 10:
            return jsonify({'error': 'weekday must be 10 characters or fewer'}), 400

        schedule_time_raw = item.get('schedule_time')
        schedule_time = _parse_time_or_none(schedule_time_raw)
        if schedule_time is None:
            return jsonify({'error': 'schedule_time must be a valid ISO time'}), 400

        row = WorkoutPlanDays()
        row.workout_plan_id = plan_id
        row.weekday = weekday
        row.schedule_time = schedule_time
        db.session.add(row)
        db.session.flush()
        created.append(_plan_day_public(row))

    db.session.commit()
    if len(created) == 1:
        return jsonify(created[0]), 201
    return jsonify({'assignments': created}), 201


@workouts_blueprint.route('/workout-plans/<int:plan_id>/assignments', methods=['GET'])
@require_auth
def list_plan_assignments(plan_id):
    """
    List workout plan assignments
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Create workout plan
            schema:
                type: array
                items:
                    type: object
                    properties:
                        id:
                            type: integer
                        workout_plan_id:
                            type: integer
                        weekday:
                            type: string
                        schedule_time:
                            type: string

        404:
            description: Workout plan not found

    """
    plan = db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == plan_id).first()
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    rows = (
        db.session.query(WorkoutPlanDays)
        .filter(WorkoutPlanDays.workout_plan_id == plan_id)
        .order_by(WorkoutPlanDays.id.asc())
        .all()
    )
    return jsonify([_plan_day_public(r) for r in rows]), 200


@workouts_blueprint.route('/workout-plan-assignments/<int:assignment_id>', methods=['DELETE'])
@require_auth
def delete_plan_assignment(assignment_id):
    """
    Delete workout plan assignment
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    message:
                        type: string

        404:
            description: Workout plan not found

    """
    assignment = db.session.query(WorkoutPlanDays).filter(WorkoutPlanDays.id == assignment_id).first()
    if assignment is None:
        return jsonify({'error': 'Workout plan assignment not found'}), 404

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@workouts_blueprint.route('/workout-plan-exercises/<int:workout_plan_exercise_id>', methods=['PUT'])
@require_auth
def update_workout_plan_exercise(workout_plan_exercise_id):
    """
    Create workout plan exercise
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          type: body
          required: true
          schema:
            type: object
            properties:
                exercise_id:
                    type: integer
                position:
                    type: integer
                sets:
                    type: integer
                reps:
                    type: integer
                weight:
                    type: number
                rpe:
                    type: number
                duration_sec:
                    type: integer
                distance_m:
                    type: number
                pace_sec_per_km:
                    type: number
                calories:
                    type: integer
                notes:
                    type: string

    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    message:
                        type: string

        400:
            description: Invalid parameters

        404:
            description: Workout plan exercise not found

    """
    pe = db.session.query(WorkoutPlanExercises).filter(
        WorkoutPlanExercises.workout_plan_exercise_id == workout_plan_exercise_id
    ).first()
    if pe is None:
        return jsonify({'error': 'Workout plan exercise not found'}), 404

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({'error': 'JSON body required'}), 400

    if 'exercise_id' in body:
        eid = _int_or_none(body.get('exercise_id'))
        if eid is None or not _exercise_exists(eid):
            return jsonify({'error': 'Invalid exercise_id'}), 400

    _apply_plan_exercise_fields(pe, body)
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200


@workouts_blueprint.route('/workout-plan-exercises/<int:workout_plan_exercise_id>', methods=['DELETE'])
@require_auth
def delete_workout_plan_exercise(workout_plan_exercise_id):
    """
    Delete workout plan exercise
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Delete workout plan exercise
            schema:
                type: object
                properties:
                    message:
                        type: string

        404:
            description: Workout plan exercise not found

    """
    pe = db.session.query(WorkoutPlanExercises).filter(
        WorkoutPlanExercises.workout_plan_exercise_id == workout_plan_exercise_id
    ).first()
    if pe is None:
        return jsonify({'error': 'Workout plan exercise not found'}), 404

    db.session.delete(pe)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@workouts_blueprint.route('/workout-plans/<int:plan_id>', methods=['DELETE'])
@require_auth
def delete_workout_plan(plan_id):
    """
    Delete workout plan
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Create workout plan
            schema:
                type: object
                properties:
                    message:
                        type: string

        404:
            description: Workout plan not found

    """
    plan = db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == plan_id).first()
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    db.session.delete(plan)
    db.session.commit()
    return jsonify({'message': 'Workout plan deleted'}), 200


# --- Workout sessions ---


@workouts_blueprint.route('/workouts', methods=['POST'])
@require_auth
def create_workout():
    """
    Create workout
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                user_id:
                    type: string
                title:
                    type: string
                workout_type_id:
                    type: integer
                workout_plan_id:
                    type: integer
                notes:
                    type: string
                mood:
                    type: integer
                duration_mins:
                    type: integer
                completion_date:
                    type: string
    responses:
        201:
            description: Create workout
            schema:
                type: object
                properties:
                    workout_id:
                        type: integer
                    user_id:
                        type: string
                    title:
                        type: string
                    workout_type_id:
                        type: integer
                    workout_plan_id:
                        type: integer
                    notes:
                        type: string
                    mood:
                        type: integer
                    duration_mins:
                        type: integer
                    completion_date:
                        type: string

        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    body = request.get_json(silent=True) or {}
    uid = _parse_uuid(body.get('user_id'))
    if uid is None:
        return jsonify({'error': 'user_id must be a valid UUID'}), 400
    if uid != g.user.user_id:
        return jsonify({'error': 'You can only create workouts for your own account'}), 403

    title = body.get('title')
    if not title or not str(title).strip():
        return jsonify({'error': 'title is required'}), 400

    w = Workouts()
    w.user_id = uid
    w.title = str(title).strip()
    w.workout_type_id = _int_or_none(body.get('workout_type_id'))
    w.workout_plan_id = _int_or_none(body.get('workout_plan_id'))
    w.notes = body.get('notes')
    w.mood = _int_or_none(body.get('mood'))
    w.duration_mins = _int_or_none(body.get('duration_mins'))
    completion_date_raw = body.get('completion_date')
    if completion_date_raw is not None:
        parsed_completion_date = _parse_datetime_or_none(completion_date_raw)
        if parsed_completion_date is None:
            return jsonify({'error': 'completion_date must be a valid ISO datetime'}), 400
        w.completion_date = parsed_completion_date

    if w.workout_type_id is not None:
        if db.session.query(WorkoutTypes).filter(WorkoutTypes.workout_type_id == w.workout_type_id).first() is None:
            return jsonify({'error': 'Invalid workout_type_id'}), 400
    if w.workout_plan_id is not None:
        if db.session.query(WorkoutPlans).filter(WorkoutPlans.workout_plan_id == w.workout_plan_id).first() is None:
            return jsonify({'error': 'Invalid workout_plan_id'}), 400

    db.session.add(w)
    db.session.commit()

    return jsonify({
        'workout_id': w.workout_id,
        'user_id': str(w.user_id),
        'title': w.title,
        'workout_type_id': w.workout_type_id,
        'workout_plan_id': w.workout_plan_id,
        'notes': w.notes,
        'mood': w.mood,
        'duration_mins': w.duration_mins,
        'completion_date': _serialize_datetime(w.completion_date),
    }), 201


@workouts_blueprint.route('/workouts/from-plan/<int:plan_id>', methods=['POST'])
@require_auth
def create_workout_from_plan(plan_id):
    """
    Create workout from plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                completion_date:
                    type: string
                notes:
                    type: string
                mood:
                    type: integer
                duration_mins:
                    type: integer
    responses:
        201:
            description: Create workout from plan
            schema:
                type: object
                properties:
                    workout_id:
                        type: integer
                    notes:
                        type: string
                    mood:
                        type: integer
                    duration_mins:
                        type: integer
                    completion_date:
                        type: string

        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    plan = (
        db.session.query(WorkoutPlans)
        .options(joinedload(WorkoutPlans.workout_plan_exercises))
        .filter(WorkoutPlans.workout_plan_id == plan_id)
        .first()
    )
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    body = request.get_json(silent=True) or {}
    completion_date_raw = body.get('completion_date')
    parsed_completion_date = _parse_datetime_or_none(completion_date_raw) if completion_date_raw is not None else None
    if completion_date_raw is not None and parsed_completion_date is None:
        return jsonify({'error': 'completion_date must be a valid ISO datetime'}), 400

    w = Workouts()
    w.user_id = g.user.user_id
    w.title = plan.title
    w.workout_type_id = plan.workout_type_id
    w.workout_plan_id = plan.workout_plan_id
    w.notes = body.get('notes')
    w.mood = _int_or_none(body.get('mood'))
    w.duration_mins = (
        _int_or_none(body.get('duration_mins'))
        if body.get('duration_mins') is not None
        else plan.duration_min
    )
    w.completion_date = parsed_completion_date
    db.session.add(w)
    db.session.flush()

    for pe in sorted(plan.workout_plan_exercises, key=lambda x: (x.position, x.workout_plan_exercise_id)):
        we = WorkoutExercises()
        we.workout_id = w.workout_id
        we.exercise_id = pe.exercise_id
        we.position = pe.position
        we.sets = pe.sets
        we.reps = pe.reps
        we.weight = pe.weight
        we.rpe = pe.rpe
        we.duration_sec = pe.duration_sec
        we.distance_m = pe.distance_m
        we.pace_sec_per_km = pe.pace_sec_per_km
        we.calories = pe.calories
        we.notes = pe.notes
        db.session.add(we)

    db.session.commit()
    return jsonify({
        'workout_id': w.workout_id,
        'notes': w.notes,
        'mood': w.mood,
        'duration_mins': w.duration_mins,
        'completion_date': _serialize_datetime(w.completion_date),
    }), 201


@workouts_blueprint.route('/workouts/<int:workout_id>', methods=['PATCH'])
@require_auth
def update_workout(workout_id):
    """
    Update workout
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                notes:
                    type: string
                mood:
                    type: integer
                duration_mins:
                    type: integer
                completion_date:
                    type: string
    responses:
        200:
            description: Update workout
            schema:
                type: object
                properties:
                    message:
                        type: string

        400:
            description: Invalid parameters

        404:
            description: Workout not found

    """
    w = db.session.query(Workouts).filter(Workouts.workout_id == workout_id).first()
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404
    if w.user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to modify this workout'}), 403

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({'error': 'JSON body required'}), 400

    if 'completion_date' in body:
        completion_date_raw = body.get('completion_date')
        if completion_date_raw is None:
            w.completion_date = None
        else:
            parsed_completion_date = _parse_datetime_or_none(completion_date_raw)
            if parsed_completion_date is None:
                return jsonify({'error': 'completion_date must be a valid ISO datetime'}), 400
            w.completion_date = parsed_completion_date

    if 'notes' in body:
        w.notes = body.get('notes')
    if 'mood' in body:
        w.mood = _int_or_none(body.get('mood'))
    if 'duration_mins' in body:
        w.duration_mins = _int_or_none(body.get('duration_mins'))

    db.session.commit()
    return jsonify({'message': 'Workout updated'}), 200


@workouts_blueprint.route('/workouts', methods=['GET'])
@require_auth
def list_user_workouts():
    """
    List user workouts
    ---
    tags:
        - Workouts
    parameters:
        - name: user_id
          in: path
          required: true
          type: string
    responses:
        200:
            description: List workouts
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_id:
                            type: integer
                        title:
                            type: string
                        notes:
                            type: string
                        mood:
                            type: integer
                        duration_mins:
                            type: integer
                        completion_date:
                            type: string

        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    uid_raw = request.args.get('user_id')
    uid = _parse_uuid(uid_raw)
    if uid is None:
        return jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400
    if uid != g.user.user_id:
        return jsonify({'error': 'You can only list your own workouts'}), 403

    rows = (
        db.session.query(
            Workouts.workout_id,
            Workouts.title,
            Workouts.notes,
            Workouts.mood,
            Workouts.duration_mins,
            Workouts.completion_date,
        )
        .filter(Workouts.user_id == uid)
        .order_by(Workouts.workout_id.desc())
        .all()
    )
    response = [
        {
            'workout_id': r.workout_id,
            'title': r.title,
            'notes': r.notes,
            'mood': r.mood,
            'duration_mins': r.duration_mins,
            'completion_date': _serialize_datetime(r.completion_date),
        }
        for r in rows
    ]
    print(f"[WORKOUTS DEBUG] GET /workouts user_id={uid} count={len(response)}", flush=True)
    print(f"[WORKOUTS DEBUG] GET /workouts response: {response}", flush=True)
    return jsonify(response), 200


@workouts_blueprint.route('/workouts/history/sets-logged', methods=['GET'])
@require_auth
def workout_sets_logged_history():
    """
    Get sets logged history
    ---
    tags:
        - Workouts
    parameters:
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
            description: Get historical sets logged
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_id:
                            type: integer
                        sets_logged:
                            type: integer
                        completion_date:
                            type: string

    """
    uid, uid_err = _require_authorized_user_id()
    if uid_err is not None:
        return uid_err

    days, days_err = _validated_days_param()
    if days_err is not None:
        return days_err

    cutoff = date.today() - timedelta(days=days - 1)
    cutoff_dt = datetime.combine(cutoff, time.min)

    rows = (
        db.session.query(
            Workouts.workout_id,
            Workouts.completion_date,
            func.coalesce(func.sum(WorkoutExercises.sets), 0).label('sets_logged'),
        )
        .outerjoin(WorkoutExercises, WorkoutExercises.workout_id == Workouts.workout_id)
        .filter(Workouts.user_id == uid)
        .filter(Workouts.completion_date.isnot(None))
        .filter(Workouts.completion_date >= cutoff_dt)
        .group_by(Workouts.workout_id, Workouts.completion_date)
        .order_by(Workouts.completion_date.asc(), Workouts.workout_id.asc())
        .all()
    )

    return jsonify([
        {
            'workout_id': r.workout_id,
            'sets_logged': int(r.sets_logged or 0),
            'completion_date': _serialize_datetime(r.completion_date),
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workouts/history/total-workout-time', methods=['GET'])
@require_auth
def workout_total_time_history():
    """
    Get workout time logged history
    ---
    tags:
        - Workouts
    parameters:
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
            description: Get historical workout time logged
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_id:
                            type: integer
                        total_workout_time:
                            type: integer
                        completion_date:
                            type: string

    """
    uid, uid_err = _require_authorized_user_id()
    if uid_err is not None:
        return uid_err

    days, days_err = _validated_days_param()
    if days_err is not None:
        return days_err

    cutoff = date.today() - timedelta(days=days - 1)
    cutoff_dt = datetime.combine(cutoff, time.min)

    rows = (
        db.session.query(
            Workouts.workout_id,
            Workouts.duration_mins,
            Workouts.completion_date,
        )
        .filter(Workouts.user_id == uid)
        .filter(Workouts.completion_date.isnot(None))
        .filter(Workouts.completion_date >= cutoff_dt)
        .order_by(Workouts.completion_date.asc(), Workouts.workout_id.asc())
        .all()
    )

    return jsonify([
        {
            'workout_id': r.workout_id,
            'total_workout_time': r.duration_mins,
            'completion_date': _serialize_datetime(r.completion_date),
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workouts/history/total-volume', methods=['GET'])
@require_auth
def workout_total_volume_history():
    """
    Get total volume logged history
    ---
    tags:
        - Workouts
    parameters:
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
            description: Get historical volume logged
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_id:
                            type: integer
                        total_volume:
                            type: integer
                        completion_date:
                            type: string

    """
    uid, uid_err = _require_authorized_user_id()
    if uid_err is not None:
        return uid_err

    days, days_err = _validated_days_param()
    if days_err is not None:
        return days_err

    cutoff = date.today() - timedelta(days=days - 1)
    cutoff_dt = datetime.combine(cutoff, time.min)

    rows = (
        db.session.query(
            Workouts.workout_id,
            Workouts.completion_date,
            func.coalesce(
                func.sum(
                    func.coalesce(WorkoutExercises.weight, 0)
                    * func.coalesce(WorkoutExercises.sets, 0)
                    * func.coalesce(WorkoutExercises.reps, 0)
                ),
                0,
            ).label('total_volume'),
        )
        .outerjoin(WorkoutExercises, WorkoutExercises.workout_id == Workouts.workout_id)
        .filter(Workouts.user_id == uid)
        .filter(Workouts.completion_date.isnot(None))
        .filter(Workouts.completion_date >= cutoff_dt)
        .group_by(Workouts.workout_id, Workouts.completion_date)
        .order_by(Workouts.completion_date.asc(), Workouts.workout_id.asc())
        .all()
    )

    return jsonify([
        {
            'workout_id': r.workout_id,
            'total_volume': _serialize_decimal(r.total_volume),
            'completion_date': _serialize_datetime(r.completion_date),
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workouts/weekly-assignments', methods=['GET'])
@workouts_blueprint.route('/workouts/current-week', methods=['GET'])
@require_auth
def list_user_weekly_assignments():
    """
    Get weekly workout assignments
    ---
    tags:
        - Workouts
    parameters:
        - name: user_id
          in: path
          required: true
          type: string
    responses:
        200:
            description: Get weekly assignments
            schema:
                type: array
                items:
                    type: object
                    properties:
                        workout_id:
                            type: integer
                        title:
                            type: string
                        workout_plan_id:
                            type: integer
                        notes:
                            type: string
                        mood:
                            type: integer
                        duration_mins:
                            type: integer
                        completion_date:
                            type: string
                        assignments:
                            type: array
                            items:
                                type: object
                                properties:
                                    id:
                                        type: integer
                                    weekday:
                                        type: string
                                    schedule_time:
                                        type: string

        400:
            description: Invalid parameters

    """
    uid_raw = request.args.get('user_id')
    uid = _parse_uuid(uid_raw)
    if uid is None:
        return jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400
    if uid != g.user.user_id:
        return jsonify({'error': 'You can only list your own workouts'}), 403

    rows = (
        db.session.query(
            Workouts.workout_id,
            Workouts.title,
            Workouts.notes,
            Workouts.mood,
            Workouts.duration_mins,
            Workouts.completion_date,
            Workouts.workout_plan_id,
            WorkoutPlanDays.id,
            WorkoutPlanDays.weekday,
            WorkoutPlanDays.schedule_time,
        )
        .outerjoin(WorkoutPlanDays, WorkoutPlanDays.workout_plan_id == Workouts.workout_plan_id)
        .filter(Workouts.user_id == uid)
        .filter(WorkoutPlanDays.id.isnot(None))
        .order_by(WorkoutPlanDays.weekday.asc(), WorkoutPlanDays.schedule_time.asc(), Workouts.workout_id.asc())
        .all()
    )

    by_workout = {}
    for r in rows:
        item = by_workout.get(r.workout_id)
        if item is None:
            item = {
                'workout_id': r.workout_id,
                'title': r.title,
                'workout_plan_id': r.workout_plan_id,
                'notes': r.notes,
                'mood': r.mood,
                'duration_mins': r.duration_mins,
                'completion_date': _serialize_datetime(r.completion_date),
                'assignments': [],
            }
            by_workout[r.workout_id] = item
        item['assignments'].append({
            'id': r.id,
            'weekday': r.weekday,
            'schedule_time': _serialize_time(r.schedule_time),
        })

    response = list(by_workout.values())
    print(f"[WORKOUTS DEBUG] GET /workouts/weekly-assignments user_id={uid} count={len(response)}", flush=True)
    print(f"[WORKOUTS DEBUG] GET /workouts/weekly-assignments response: {response}", flush=True)
    return jsonify(response), 200

@workouts_blueprint.route("/workouts/my_schedule", methods=['GET'])
@require_auth
def get_user_schedule():
    """
        Get weekly workout assignments
        ---
        tags:
            - Workouts
        parameters:
            - name: user_id
              in: query
              required: true
              type: string
        responses:
            200:
                description: Get schedule
                schema:
                    type: object
                    properties:
                        my_schedule:
                            type: array
                            items:
                                type: object
                                properties:
                                    assignment_id:
                                        type: integer
                                    weekday:
                                        type: string
                                    schedule_time:
                                        type: string
                                    workout_plan_id:
                                        type: integer
                                    title:
                                        type: string
                                    duration_mins:
                                        type: integer

            400:
                description: Invalid parameters

    """
    uid_raw = request.args.get('user_id')
    target_uid = _parse_uuid(uid_raw)
    requester_uid = g.user.user_id
    if target_uid is None:
        return jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400
    if target_uid != requester_uid:
        return jsonify({'error': 'You can only list your own workouts'}), 403
    rows = (
        db.session.query(
            WorkoutPlanDays.id,
            WorkoutPlanDays.weekday,
            WorkoutPlanDays.schedule_time,
            WorkoutPlans.workout_plan_id,
            WorkoutPlans.title,
            WorkoutPlans.duration_min
        )
        .join(WorkoutPlans, WorkoutPlans.workout_plan_id == WorkoutPlanDays.workout_plan_id)
        .filter(WorkoutPlans.created_by == target_uid)
        .order_by(WorkoutPlanDays.weekday.desc(), WorkoutPlanDays.schedule_time.asc())
        .all()
    )

    return jsonify(
        {
            "my_schedule": [
                {
                    'assignment_id': r.id,
                    'weekday': r.weekday, 
                    'schedule_time': _serialize_time(r.schedule_time),
                    'workout_plan_id': r.workout_plan_id,
                    'title': r.title,
                    'duration_min': r.duration_min
                }
                for r in rows
            ]
        }
    ), 200

@workouts_blueprint.route('/workouts/<int:workout_id>', methods=['GET'])
@require_auth
def get_workout(workout_id):
    """
        Get workout
        ---
        tags:
            - Workouts
        responses:
            200:
                description: Get weekly assignments
                schema:
                    type: array
                    items:
                        type: object
                        properties:
                            workout_id:
                                type: integer
                            user_id:
                                type: string
                            title:
                                type: string
                            workout_type_id:
                                type: integer
                            workout_plan_id:
                                type: integer
                            notes:
                                type: string
                            mood:
                                type: string
                            duration_mins:
                                type: string
                            completion_date:
                                type: string
                            assignments:
                                type: array
                                items:
                                    type: object
                                    properties:
                                        id:
                                            type: integer
                                        workout_plan_id:
                                            type: integer
                                        weekday:
                                            type: string
                                        schedule_time:
                                            type: string
                            exercises:
                                type: array
                                items:
                                    type: object
                                    properties:
                                        workout_plan_exercise_id:
                                            type: integer
                                        workout_plan_id:
                                            type: integer
                                        exercise_id:
                                            type: integer
                                        name:
                                            type: string
                                        position:
                                            type: integer
                                        sets:
                                            type: integer
                                        reps:
                                            type: integer
                                        weight:
                                            type: number
                                        rpe:
                                            type: number
                                        duration_sec:
                                            type: integer
                                        distance_m:
                                            type: number
                                        pace_sec_per_km:
                                            type: number
                                        calories:
                                            type: integer
                                        notes:
                                            type: string

            404:
                description: Workout not found

    """
    w = _get_workout_for_user(workout_id, g.user.user_id)
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404

    exercises = sorted(w.workout_exercises, key=lambda x: (x.position, x.workout_exercise_id))
    response = {
        'workout_id': w.workout_id,
        'user_id': str(w.user_id),
        'title': w.title,
        'workout_type_id': w.workout_type_id,
        'workout_plan_id': w.workout_plan_id,
        'notes': w.notes,
        'mood': w.mood,
        'duration_mins': w.duration_mins,
        'completion_date': _serialize_datetime(w.completion_date),
        'assignments': [_plan_day_public(d) for d in sorted(w.workout_plan.workout_plan_days, key=lambda x: x.id)] if w.workout_plan else [],
        'exercises': [_workout_exercise_public(we) for we in exercises],
    }
    print(f"[WORKOUTS DEBUG] GET /workouts/{workout_id} user_id={g.user.user_id}", flush=True)
    print(f"[WORKOUTS DEBUG] GET /workouts/{workout_id} response: {response}", flush=True)
    return jsonify(response), 200


@workouts_blueprint.route('/workouts/<int:workout_id>', methods=['DELETE'])
@require_auth
def delete_workout(workout_id):
    """
        Delete workout
        ---
        tags:
            - Workouts
        responses:
            200:
                description: Delete workout
                schema:
                    type: object
                    properties:
                        message:
                            type: string

            404:
                description: Workout not found

    """
    w = db.session.query(Workouts).filter(Workouts.workout_id == workout_id).first()
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404
    if w.user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to delete this workout'}), 403

    db.session.delete(w)
    db.session.commit()
    return jsonify({'message': 'Workout deleted'}), 200


@workouts_blueprint.route('/workouts/<int:workout_id>/exercises', methods=['GET'])
@require_auth
def list_workout_exercises(workout_id):
    """
        List workout exercises
        ---
        tags:
            - Workouts
        responses:
            200:
                description: Get workout exercises
                schema:
                    type: array
                    items:
                        type: object
                        properties:
                            workout_plan_exercise_id:
                                type: integer
                            workout_plan_id:
                                type: integer
                            exercise_id:
                                type: integer
                            name:
                                type: string
                            position:
                                type: integer
                            sets:
                                type: integer
                            reps:
                                type: integer
                            weight:
                                type: number
                            rpe:
                                type: number
                            duration_sec:
                                type: integer
                            distance_m:
                                type: number
                            pace_sec_per_km:
                                type: number
                            calories:
                                type: integer
                            notes:
                                type: string

            404:
                description: Workout not found

    """
    w = _get_workout_for_user(workout_id, g.user.user_id)
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404

    exercises = sorted(w.workout_exercises, key=lambda x: (x.position, x.workout_exercise_id))
    return jsonify([_workout_exercise_public(we) for we in exercises]), 200


@workouts_blueprint.route('/workouts/<int:workout_id>/exercises', methods=['POST'])
@require_auth
def add_workout_exercises(workout_id):
    """
    Add exercise to workout plan
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                exercises:
                    type: array
                    items:
                        type: object
                        properties:
                            exercise_id:
                                type: integer
                            position:
                                type: integer
    responses:
        200:
            description: Add workout exercise
            schema:
                type: object
                properties:
                    workout_exercise_ids:
                        type: array
                        items:
                            type: integer
        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    w = db.session.query(Workouts).filter(Workouts.workout_id == workout_id).first()
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404
    if w.user_id != g.user.user_id:
        return jsonify({'error': 'You are not authorized to modify this workout'}), 403

    body = request.get_json(silent=True) or {}
    items = body.get('exercises')
    if items is None:
        items = [body]
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Send a single exercise object or { "exercises": [ ... ] }'}), 400

    created_ids = []
    for item in items:
        eid = _int_or_none(item.get('exercise_id'))
        if eid is None or not _exercise_exists(eid):
            return jsonify({'error': f'Invalid exercise_id: {item.get("exercise_id")}'}), 400
        row = WorkoutExercises()
        row.workout_id = workout_id
        row.exercise_id = eid
        row.position = _int_or_none(item.get('position')) if item.get('position') is not None else 0
        _apply_workout_exercise_fields(row, {k: v for k, v in item.items() if k != 'exercise_id'})
        db.session.add(row)
        db.session.flush()
        created_ids.append(row.workout_exercise_id)

    db.session.commit()

    if len(created_ids) == 1:
        return jsonify({'workout_exercise_id': created_ids[0]}), 201
    return jsonify({'workout_exercise_ids': created_ids}), 201


@workouts_blueprint.route('/workout-exercises/<int:workout_exercise_id>', methods=['PUT'])
@require_auth
def update_workout_exercise(workout_exercise_id):
    """
    Update workout exercise
    ---
    tags:
        - Workouts
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                position:
                    type: integer
                sets:
                    type: integer
                reps:
                    type: integer
                weight:
                    type: number
                rpe:
                    type: number
                duration_sec:
                    type: integer
                distance_m:
                    type: number
                pace_sec_per_km:
                    type: number
                calories:
                    type: integer
                notes:
                    type: string

    responses:
        200:
            description: Update workout exercise
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters

        404:
            description: Workout plan not found

    """
    we = (
        db.session.query(WorkoutExercises)
        .join(Workouts, Workouts.workout_id == WorkoutExercises.workout_id)
        .filter(
            WorkoutExercises.workout_exercise_id == workout_exercise_id,
            Workouts.user_id == g.user.user_id,
        )
        .first()
    )
    if we is None:
        return jsonify({'error': 'Workout exercise not found'}), 404

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({'error': 'JSON body required'}), 400

    if 'exercise_id' in body:
        eid = _int_or_none(body.get('exercise_id'))
        if eid is None or not _exercise_exists(eid):
            return jsonify({'error': 'Invalid exercise_id'}), 400

    _apply_workout_exercise_fields(we, body)
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200


@workouts_blueprint.route('/workout-exercises/<int:workout_exercise_id>', methods=['DELETE'])
@require_auth
def delete_workout_exercise(workout_exercise_id):
    """
    Update workout exercise
    ---
    tags:
        - Workouts
    responses:
        200:
            description: Delete workout exercise
            schema:
                type: object
                properties:
                    message:
                        type: string

        404:
            description: Workout plan not found

    """
    we = (
        db.session.query(WorkoutExercises)
        .join(Workouts, Workouts.workout_id == WorkoutExercises.workout_id)
        .filter(
            WorkoutExercises.workout_exercise_id == workout_exercise_id,
            Workouts.user_id == g.user.user_id,
        )
        .first()
    )
    if we is None:
        return jsonify({'error': 'Workout exercise not found'}), 404

    db.session.delete(we)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200
