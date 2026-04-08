from datetime import datetime, timezone
from uuid import UUID

from models import ClientGoals, CoachSurveys, Users, db
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g

users_blueprint = Blueprint('users_blueprint', __name__)

_PRIMARY_GOALS_BINARY_CHARS = {'0', '1'}


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes')
    return bool(value)


def _firebase_uid():
    tok = g.firebase_user
    return tok.get('uid') or tok.get('user_id') or tok.get('sub')


def _parse_uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _ensure_self(user_id_str):
    uid = _parse_uuid(user_id_str)
    if uid is None:
        return None, (jsonify({'error': 'Invalid user id'}), 400)
    if uid != g.user.user_id:
        return None, (jsonify({'error': 'You are not authorized to access this resource'}), 403)
    return uid, None


def _validate_primary_goals_binary(value):
    if value is None:
        return None
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


def _latest_coach_survey(user_id):
    return (
        db.session.query(CoachSurveys)
        .filter(CoachSurveys.user_id == user_id)
        .order_by(CoachSurveys.date_created.desc())
        .first()
    )


def _now_naive_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@users_blueprint.route('/register', methods=['POST'])
@require_auth
def register_user():
    body = request.get_json(silent=True) or {}
    firebase_uid = _firebase_uid()

    if db.session.query(Users).filter(Users.firebase_user_id == firebase_uid).first():
        return jsonify({'error': 'This Firebase account is already registered'}), 409

    first_name = body.get('first_name')
    last_name = body.get('last_name')
    email = body.get('email')
    if first_name is None or last_name is None or email is None:
        return jsonify({'error': 'JSON must include first_name, last_name, and email'}), 400

    is_coach = body.get('is_coach')
    if is_coach is None:
        return jsonify({'error': 'JSON must include is_coach'}), 400
    is_coach = _coerce_bool(is_coach)
    if 'is_client' in body:
        is_client = _coerce_bool(body.get('is_client'))
        # Initial registration must choose exactly one role.
        if is_client == is_coach:
            return jsonify({'error': 'At registration, exactly one of is_coach or is_client must be true'}), 400
    else:
        is_client = not is_coach

    is_active = body.get('is_active', True)

    new_user = Users()
    new_user.firebase_user_id = firebase_uid
    new_user.first_name = first_name
    new_user.last_name = last_name
    new_user.email = email
    new_user.is_coach = is_coach
    new_user.is_client = is_client
    new_user.is_active = _coerce_bool(is_active)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'user_id': str(new_user.user_id),
        'first_name': new_user.first_name,
        'last_name': new_user.last_name,
        'email': new_user.email,
        'is_coach': new_user.is_coach,
        'is_client': new_user.is_client,
        'is_active': new_user.is_active,
        'date_created': new_user.date_created.isoformat() if new_user.date_created else None,
    }), 201


@users_blueprint.route('/me', methods=['GET'])
@require_auth
def get_me():
    return jsonify({
        'user_id': str(g.user.user_id),
        'is_coach': g.user.is_coach,
        'is_client': g.user.is_client,
    }), 200


@users_blueprint.route('/onboarding/submit_client_survey', methods=['POST'])
@require_auth
def submit_client_survey():
    if db.session.query(ClientGoals).filter(ClientGoals.user_id == g.user.user_id).count() > 0:
        return jsonify({
            'error': 'A client survey already exists for this user. Use PATCH /users/onboarding/client_survey to update it.',
        }), 409

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
    g.user.is_client = True

    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'user_survey_id': new_goal.user_survey_id,
        'user_id': str(new_goal.user_id),
        'primary_goals_binary': new_goal.primary_goals,
        'weight_goal': new_goal.weight_goal,
        'exercise_minutes_goal': new_goal.exercise_minutes_goal,
        'personal_goals': new_goal.personal_goals,
        'date_created': new_goal.date_created.isoformat() if new_goal.date_created else None,
        'last_updated': new_goal.last_updated.isoformat() if new_goal.last_updated else None,
    }), 201


@users_blueprint.route('/onboarding/client_survey', methods=['PATCH'])
@require_auth
def patch_client_survey():
    body = request.get_json(silent=True) or {}
    survey = None
    if (sid := body.get('user_survey_id')) is not None:
        survey = db.session.query(ClientGoals).filter(ClientGoals.user_survey_id == sid).first()
        if survey is None:
            return jsonify({'error': 'Survey not found'}), 404
        if survey.user_id != g.user.user_id:
            return jsonify({'error': 'You are not authorized to modify this survey'}), 403
    else:
        survey = _latest_client_survey(g.user.user_id)
        if survey is None:
            return jsonify({'error': 'No client survey to update. Use POST /users/onboarding/submit_client_survey first.'}), 404

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
    g.user.is_client = True
    db.session.commit()

    return jsonify({
        'user_survey_id': survey.user_survey_id,
        'user_id': str(survey.user_id),
        'primary_goals_binary': survey.primary_goals,
        'weight_goal': survey.weight_goal,
        'exercise_minutes_goal': survey.exercise_minutes_goal,
        'personal_goals': survey.personal_goals,
        'date_created': survey.date_created.isoformat() if survey.date_created else None,
        'last_updated': survey.last_updated.isoformat() if survey.last_updated else None,
    }), 200


@users_blueprint.route('/onboarding/submit_coach_survey', methods=['POST'])
@require_auth
def submit_coach_survey():
    if db.session.query(CoachSurveys).filter(CoachSurveys.user_id == g.user.user_id).count() > 0:
        return jsonify({
            'error': 'A coach survey already exists. Use PATCH /users/onboarding/coach_survey to update it.',
        }), 409

    body = request.get_json(silent=True) or {}
    specialization = body.get('specialization')
    if not specialization or not str(specialization).strip():
        return jsonify({'error': 'JSON must include specialization'}), 400
    specialization = str(specialization).strip()
    if len(specialization) > 20:
        return jsonify({'error': 'specialization must be at most 20 characters'}), 400

    coach_cost = body.get('coach_cost')
    if coach_cost is not None:
        try:
            coach_cost = int(coach_cost)
        except (TypeError, ValueError):
            return jsonify({'error': 'coach_cost must be an integer'}), 400
        if coach_cost < 0:
            return jsonify({'error': 'coach_cost must be >= 0'}), 400

    row = CoachSurveys()
    row.user_id = g.user.user_id
    row.specialization = specialization
    row.last_update = _now_naive_utc()
    g.user.is_coach = True
    if coach_cost is not None:
        g.user.coach_cost = coach_cost

    db.session.add(row)
    db.session.commit()

    return jsonify({
        'coach_survey_id': row.coach_survey_id,
        'user_id': str(row.user_id),
        'specialization': row.specialization,
        'coach_cost': g.user.coach_cost,
        'date_created': row.date_created.isoformat() if row.date_created else None,
        'last_update': row.last_update.isoformat() if row.last_update else None,
    }), 201


@users_blueprint.route('/onboarding/coach_survey', methods=['PATCH'])
@require_auth
def patch_coach_survey():
    body = request.get_json(silent=True) or {}
    survey = None
    if (sid := body.get('coach_survey_id')) is not None:
        survey = db.session.query(CoachSurveys).filter(CoachSurveys.coach_survey_id == sid).first()
        if survey is None:
            return jsonify({'error': 'Survey not found'}), 404
        if survey.user_id != g.user.user_id:
            return jsonify({'error': 'You are not authorized to modify this survey'}), 403
    else:
        survey = _latest_coach_survey(g.user.user_id)
        if survey is None:
            return jsonify({'error': 'No coach survey to update. Use POST /users/onboarding/submit_coach_survey first.'}), 404

    if 'specialization' in body:
        spec = body['specialization']
        if spec is None or not str(spec).strip():
            return jsonify({'error': 'specialization must be a non-empty string'}), 400
        spec = str(spec).strip()
        if len(spec) > 20:
            return jsonify({'error': 'specialization must be at most 20 characters'}), 400
        survey.specialization = spec

    if 'coach_cost' in body:
        coach_cost = body['coach_cost']
        if coach_cost is None:
            g.user.coach_cost = None
        else:
            try:
                coach_cost = int(coach_cost)
            except (TypeError, ValueError):
                return jsonify({'error': 'coach_cost must be an integer'}), 400
            if coach_cost < 0:
                return jsonify({'error': 'coach_cost must be >= 0'}), 400
            g.user.coach_cost = coach_cost

    survey.last_update = _now_naive_utc()
    g.user.is_coach = True
    db.session.commit()

    return jsonify({
        'coach_survey_id': survey.coach_survey_id,
        'user_id': str(survey.user_id),
        'specialization': survey.specialization,
        'coach_cost': g.user.coach_cost,
        'date_created': survey.date_created.isoformat() if survey.date_created else None,
        'last_update': survey.last_update.isoformat() if survey.last_update else None,
    }), 200


@users_blueprint.route('/<user_id>/profile', methods=['GET'])
@require_auth
def get_user_profile(user_id):
    _, err = _ensure_self(user_id)
    if err:
        return err

    u = g.user
    payload = {
        'user_id': str(u.user_id),
        'first_name': u.first_name,
        'last_name': u.last_name,
        'email': u.email,
        'is_coach': u.is_coach,
        'is_client': u.is_client,
        'coach_cost': u.coach_cost,
        'is_active': u.is_active,
        'date_created': u.date_created.isoformat() if u.date_created else None,
    }

    if u.is_coach:
        cs = _latest_coach_survey(u.user_id)
        payload['coach_survey'] = None if cs is None else {
            'coach_survey_id': cs.coach_survey_id,
            'specialization': cs.specialization,
            'date_created': cs.date_created.isoformat() if cs.date_created else None,
            'last_update': cs.last_update.isoformat() if cs.last_update else None,
        }
    else:
        payload['coach_survey'] = None

    if u.is_client:
        cg = _latest_client_survey(u.user_id)
        payload['client_goals'] = None if cg is None else {
            'user_survey_id': cg.user_survey_id,
            'primary_goals_binary': cg.primary_goals,
            'weight_goal': cg.weight_goal,
            'exercise_minutes_goal': cg.exercise_minutes_goal,
            'personal_goals': cg.personal_goals,
            'date_created': cg.date_created.isoformat() if cg.date_created else None,
            'last_updated': cg.last_updated.isoformat() if cg.last_updated else None,
        }
    else:
        payload['client_goals'] = None

    return jsonify(payload), 200


@users_blueprint.route('/<user_id>/edit_account', methods=['PATCH'])
@require_auth
def edit_user_account(user_id):
    _, err = _ensure_self(user_id)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({'error': 'JSON body required'}), 400

    if 'first_name' in body:
        g.user.first_name = body['first_name']
    if 'last_name' in body:
        g.user.last_name = body['last_name']
    if 'email' in body:
        g.user.email = body['email']

    db.session.commit()

    return jsonify({
        'user_id': str(g.user.user_id),
        'first_name': g.user.first_name,
        'last_name': g.user.last_name,
        'email': g.user.email,
    }), 200


@users_blueprint.route('/<user_id>/delete_account', methods=['POST'])
@require_auth
def delete_user_account(user_id):
    _, err = _ensure_self(user_id)
    if err:
        return err

    g.user.is_active = False
    db.session.commit()

    return jsonify({'message': 'Account deactivated', 'user_id': str(g.user.user_id), 'is_active': False}), 200
