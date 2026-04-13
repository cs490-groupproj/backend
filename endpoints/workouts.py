from decimal import Decimal
from datetime import datetime, timedelta
from uuid import UUID

from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g
from sqlalchemy.orm import joinedload

from models import (
    BodyParts,
    ExerciseCategories,
    Exercises,
    WorkoutExercises,
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


def _parse_schedule_date(value):
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


def _workout_exercise_public(we: WorkoutExercises):
    ex = we.exercise
    return {
        'workout_exercise_id': we.workout_exercise_id,
        'workout_id': we.workout_id,
        'exercise_id': we.exercise_id,
        'name': ex.name if ex else None,
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
    rows = db.session.query(ExerciseCategories).order_by(ExerciseCategories.name).all()
    return jsonify([{'category_id': r.category_id, 'name': r.name} for r in rows]), 200


@workouts_blueprint.route('/body-parts', methods=['GET'])
@require_auth
def list_body_parts():
    rows = db.session.query(BodyParts).order_by(BodyParts.name).all()
    return jsonify([{'body_part_id': r.body_part_id, 'name': r.name} for r in rows]), 200


@workouts_blueprint.route('/workout-types', methods=['GET'])
@require_auth
def list_workout_types():
    rows = db.session.query(WorkoutTypes).order_by(WorkoutTypes.name).all()
    return jsonify([{'workout_type_id': r.workout_type_id, 'name': r.name} for r in rows]), 200


# --- Master exercises ---


@workouts_blueprint.route('/exercises', methods=['GET'])
@require_auth
def list_exercises():
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
            'body_part_id': e.body_part_id,
            'category_id': e.category_id,
            'body_part': e.body_part.name if e.body_part else None,
            'category': e.category.name if e.category else None,
        })
    return jsonify(out), 200


@workouts_blueprint.route('/exercises/<int:exercise_id>', methods=['GET'])
@require_auth
def get_exercise(exercise_id):
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
        'body_part_id': e.body_part_id,
        'category_id': e.category_id,
        'body_part': e.body_part.name if e.body_part else None,
        'category': e.category.name if e.category else None,
    }), 200


# --- Workout plans (templates) ---


@workouts_blueprint.route('/workout-plans', methods=['GET'])
@require_auth
def list_workout_plans():
    rows = db.session.query(WorkoutPlans).order_by(WorkoutPlans.title).all()
    return jsonify([{'workout_plan_id': r.workout_plan_id, 'title': r.title} for r in rows]), 200


@workouts_blueprint.route('/workout-plans/<int:plan_id>', methods=['GET'])
@require_auth
def get_workout_plan(plan_id):
    plan = (
        db.session.query(WorkoutPlans)
        .options(
            joinedload(WorkoutPlans.workout_plan_exercises).joinedload(WorkoutPlanExercises.exercise)
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
        'exercises': [_plan_exercise_public(pe) for pe in exercises],
    }), 200


@workouts_blueprint.route('/workout-plans', methods=['POST'])
@require_auth
def create_workout_plan():
    body = request.get_json(silent=True) or {}
    title = body.get('title')
    if not title or not str(title).strip():
        return jsonify({'error': 'title is required'}), 400

    plan = WorkoutPlans()
    plan.title = str(title).strip()
    plan.workout_type_id = _int_or_none(body.get('workout_type_id'))
    plan.description = body.get('description')
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


# --- Workout sessions ---


@workouts_blueprint.route('/workouts', methods=['POST'])
@require_auth
def create_workout():
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
    schedule_date = body.get('schedule_date')
    parsed_schedule_date = _parse_schedule_date(schedule_date) if schedule_date is not None else None
    if schedule_date is not None and parsed_schedule_date is None:
        return jsonify({'error': 'schedule_date must be a valid ISO datetime'}), 400
    w.schedule_date = parsed_schedule_date or datetime.now()

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
        'schedule_date': _serialize_datetime(w.schedule_date),
    }), 201


@workouts_blueprint.route('/workouts/from-plan/<int:plan_id>', methods=['POST'])
@require_auth
def create_workout_from_plan(plan_id):
    plan = (
        db.session.query(WorkoutPlans)
        .options(joinedload(WorkoutPlans.workout_plan_exercises))
        .filter(WorkoutPlans.workout_plan_id == plan_id)
        .first()
    )
    if plan is None:
        return jsonify({'error': 'Workout plan not found'}), 404

    body = request.get_json(silent=True) or {}
    schedule_date = body.get('schedule_date')
    parsed_schedule_date = _parse_schedule_date(schedule_date) if schedule_date is not None else None
    if schedule_date is not None and parsed_schedule_date is None:
        return jsonify({'error': 'schedule_date must be a valid ISO datetime'}), 400

    w = Workouts()
    w.user_id = g.user.user_id
    w.title = plan.title
    w.workout_type_id = plan.workout_type_id
    w.workout_plan_id = plan.workout_plan_id
    w.schedule_date = parsed_schedule_date or datetime.now()
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
        'schedule_date': _serialize_datetime(w.schedule_date),
    }), 201


@workouts_blueprint.route('/workouts', methods=['GET'])
@require_auth
def list_user_workouts():
    uid_raw = request.args.get('user_id')
    uid = _parse_uuid(uid_raw)
    if uid is None:
        return jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400
    if uid != g.user.user_id:
        return jsonify({'error': 'You can only list your own workouts'}), 403

    rows = (
        db.session.query(Workouts.workout_id, Workouts.title, Workouts.schedule_date)
        .filter(Workouts.user_id == uid)
        .order_by(Workouts.workout_id.desc())
        .all()
    )
    return jsonify([
        {
            'workout_id': r.workout_id,
            'title': r.title,
            'schedule_date': _serialize_datetime(r.schedule_date),
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workouts/current-week', methods=['GET'])
@require_auth
def list_user_workouts_current_week():
    uid_raw = request.args.get('user_id')
    uid = _parse_uuid(uid_raw)
    if uid is None:
        return jsonify({'error': 'Query parameter user_id (UUID) is required'}), 400
    if uid != g.user.user_id:
        return jsonify({'error': 'You can only list your own workouts'}), 403

    now = datetime.now()
    start_of_week = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=7)

    rows = (
        db.session.query(Workouts.workout_id, Workouts.title, Workouts.schedule_date)
        .filter(Workouts.user_id == uid)
        .filter(Workouts.schedule_date >= start_of_week, Workouts.schedule_date < end_of_week)
        .order_by(Workouts.schedule_date.asc(), Workouts.workout_id.asc())
        .all()
    )
    return jsonify([
        {
            'workout_id': r.workout_id,
            'title': r.title,
            'schedule_date': _serialize_datetime(r.schedule_date),
        }
        for r in rows
    ]), 200


@workouts_blueprint.route('/workouts/<int:workout_id>', methods=['GET'])
@require_auth
def get_workout(workout_id):
    w = _get_workout_for_user(workout_id, g.user.user_id)
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404

    exercises = sorted(w.workout_exercises, key=lambda x: (x.position, x.workout_exercise_id))
    return jsonify({
        'workout_id': w.workout_id,
        'user_id': str(w.user_id),
        'title': w.title,
        'workout_type_id': w.workout_type_id,
        'workout_plan_id': w.workout_plan_id,
        'schedule_date': _serialize_datetime(w.schedule_date),
        'exercises': [_workout_exercise_public(we) for we in exercises],
    }), 200


@workouts_blueprint.route('/workouts/<int:workout_id>', methods=['DELETE'])
@require_auth
def delete_workout(workout_id):
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
    w = _get_workout_for_user(workout_id, g.user.user_id)
    if w is None:
        return jsonify({'error': 'Workout not found'}), 404

    exercises = sorted(w.workout_exercises, key=lambda x: (x.position, x.workout_exercise_id))
    return jsonify([_workout_exercise_public(we) for we in exercises]), 200


@workouts_blueprint.route('/workouts/<int:workout_id>/exercises', methods=['POST'])
@require_auth
def add_workout_exercises(workout_id):
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
