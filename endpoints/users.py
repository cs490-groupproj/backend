from datetime import datetime, timezone
from uuid import UUID

from firebase_admin import auth as firebase_auth
from models import ClientGoals, CoachSurveys, Users, db
from auth.authentication import require_auth
from flask import Blueprint, jsonify, request, g

from auth.util import can_access_client_endpoint  # add import

users_blueprint = Blueprint('users_blueprint', __name__)

_PRIMARY_GOALS_BINARY_CHARS = {'0', '1'}
_COACH_QUALIFICATIONS_MAX_LEN = 1000



def _ensure_self_or_coached_client(user_id_str):
    uid = _parse_uuid(user_id_str)
    if uid is None:
        return None, (jsonify({'error': 'Invalid user id'}), 400)
    if not can_access_client_endpoint(g.user, uid, g.clients_ids):
        return None, (jsonify({'error': 'You are not authorized to access this resource'}), 403)
    return uid, None

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


def _validate_optional_qualifications(value):
    if value is None:
        return None, None
    text_value = str(value).strip()
    if len(text_value) > _COACH_QUALIFICATIONS_MAX_LEN:
        return None, jsonify({'error': f'qualifications must be at most {_COACH_QUALIFICATIONS_MAX_LEN} characters'})
    return text_value, None


@users_blueprint.route('/register', methods=['POST'])
@require_auth
def register_user():
    """
    Register a new user
    ---
    tags:
        - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
            type: object
            properties:
                first_name:
                    type: string
                last_name:
                    type: string
                email:
                    type: string
                is_coach:
                    type: integer
                is_client:
                    type: integer
                is_active:
                    type: integer
                    required: false
    responses:
        201:
            description: Register a user
            schema:
                type: object
                properties:
                    user_id:
                        type: string
                    first_name:
                        type: string
                    last_name:
                        type: string
                    email:
                        type: string
                    is_coach:
                        type: integer
                    is_client:
                        type: integer
                    is_active:
                        type: integer
        400:
            description: Error with parameters

        409:
            description: User is already registered
    """
    body = request.get_json(silent=True) or {}
    firebase_uid = _firebase_uid()

    if db.session.query(Users).filter(Users.firebase_user_id == firebase_uid).first():
        return jsonify({'error': 'This Firebase account is already registered'}), 409

    first_name = body.get('first_name')
    last_name = body.get('last_name')
    email = body.get('email')
    if first_name is None or last_name is None or email is None:
        return jsonify({'error': 'JSON must include first_name, last_name, and email'}), 400

    is_active = body.get('is_active', True)

    new_user = Users()
    new_user.firebase_user_id = firebase_uid
    new_user.first_name = first_name
    new_user.last_name = last_name
    new_user.email = email
    new_user.is_coach = False
    new_user.is_client = True
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
    """
    Get logged-in user ID
    ---
    tags:
        - Users
    responses:
        200:
            description: Get current user
            schema:
                type: object
                properties:
                    user_id:
                        type: string
                    is_coach:
                        type: boolean
                    is_client:
                        type: boolean
                    is_admin:
                        type: boolean
    """
    return jsonify({
        'user_id': str(g.user.user_id),
        'is_coach': g.user.is_coach,
        'is_client': g.user.is_client,
        'is_admin': g.user.is_admin,
    }), 200


@users_blueprint.route('/onboarding/submit_coach_survey', methods=['POST'])
@require_auth
def submit_coach_survey():
    """
    Submit initial coach onboarding survey
    ---
    tags:
        - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
            type: object
            properties:
                specialization:
                    type: string
                qualifications:
                    type: string
                coach_cost:
                    type: integer
    responses:
        201:
            description: Submit onboarding survey
            schema:
                type: object
                properties:
                    coach_survey_id:
                        type: integer
                    user_id:
                        type: string
                    specialization:
                        type: string
                    qualifications:
                        type: string
                    coach_cost:
                        type: integer
                    date_created:
                        type: string
                    last_updated:
                        type: string

        400:
            description: Error with parameters

        409:
            description: User has already submitted a coach survey
        """
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

    qualifications, q_err = _validate_optional_qualifications(body.get('qualifications'))
    if q_err is not None:
        return q_err, 400

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
    row.qualifications = qualifications
    row.last_update = _now_naive_utc()
    row.is_client = True
    if coach_cost is not None:
        g.user.coach_cost = coach_cost

    db.session.add(row)
    db.session.commit()

    return jsonify({
        'coach_survey_id': row.coach_survey_id,
        'user_id': str(row.user_id),
        'specialization': row.specialization,
        'qualifications': row.qualifications,
        'coach_cost': g.user.coach_cost,
        'date_created': row.date_created.isoformat() if row.date_created else None,
        'last_update': row.last_update.isoformat() if row.last_update else None,
    }), 201


# NOTE: This will be moved to the coaches blueprint in the future
@users_blueprint.route('/onboarding/coach_survey', methods=['PATCH'])
@require_auth
def patch_coach_survey():
    """
    Update coach onboarding survey
    ---
    tags:
        - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
            type: object
            properties:
                coach_survey_id:
                    type: integer
                specialization:
                    type: string
                qualifications:
                    type: string
                coach_cost:
                    type: integer
    responses:
        200:
            description: Update onboarding survey
            schema:
                type: object
                properties:
                    coach_survey_id:
                        type: integer
                    user_id:
                        type: string
                    specialization:
                        type: string
                    qualifications:
                        type: string
                    coach_cost:
                        type: integer
                    date_created:
                        type: string
                    last_updated:
                        type: string

        400:
            description: Error with parameters

        404:
            description: Survey not found

        409:
            description: User has already submitted a coach survey
        """
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

    if 'qualifications' in body:
        qualifications, q_err = _validate_optional_qualifications(body.get('qualifications'))
        if q_err is not None:
            return q_err, 400
        survey.qualifications = qualifications

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
        'qualifications': survey.qualifications,
        'coach_cost': g.user.coach_cost,
        'date_created': survey.date_created.isoformat() if survey.date_created else None,
        'last_update': survey.last_update.isoformat() if survey.last_update else None,
    }), 200


@users_blueprint.route('/<user_id>/profile', methods=['GET'])
@require_auth
def get_user_profile(user_id):
    """
    Get user profile
    ---
    tags:
        - Users
    responses:
        200:
            description: Get user profile
            schema:
                type: object
                properties:
                    user_id:
                        type: string
                    first_name:
                        type: string
                    last_name:
                        type: string
                    email:
                        type: string
                    is_coach:
                        type: string
                    is_client:
                        type: string
                    is_admin:
                        type: string
                    coach_cost:
                        type: integer
                    is_active:
                        type: boolean
                    date_created:
                        type: string
                    coach_survey:
                        type: object
                        properties:
                            coach_survey_id:
                                type: integer
                            specialization:
                                type: integer
                            qualifications:
                                type: integer
                            date_created:
                                type: string
                            last_updated:
                                type: string
                    client_goals:
                        type: object
                        properties:
                            user_survey_id:
                                type: integer
                            primary_goals_binary:
                                type: string
                            weight_goal:
                                type: integer
                            exercise_minutes_goal:
                                type: integer
                            personal_goals:
                                type: string
                            date_created:
                                type: string
                            last_modified:
                                type: string

        400:
            description: Error with parameters

        409:
            description: User has already submitted a coach survey
        """
    target_uid, err = _ensure_self(user_id)
    if err:
        return err
    u = db.session.query(Users).filter(Users.user_id == target_uid).first()
    if u is None:
        return jsonify({'error': 'User not found'}), 404
    payload = {
        'user_id': str(u.user_id),
        'first_name': u.first_name,
        'last_name': u.last_name,
        'email': u.email,
        'is_coach': u.is_coach,
        'is_client': u.is_client,
        'is_admin': u.is_admin,
        'coach_cost': u.coach_cost,
        'is_active': u.is_active,
        'date_created': u.date_created.isoformat() if u.date_created else None,
    }

    if u.is_coach:
        cs = _latest_coach_survey(u.user_id)
        payload['coach_survey'] = None if cs is None else {
            'coach_survey_id': cs.coach_survey_id,
            'specialization': cs.specialization,
            'qualifications': cs.qualifications,
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
    """
    Edit user account
    ---
    tags:
        - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
            type: object
            properties:
                first_name:
                    type: string
                last_name:
                    type: string
                email:
                    type: string
    responses:
        200:
            description: Edit user account
            schema:
                type: object
                properties:
                    user_id:
                        type: string
                    first_name:
                        type: string
                    last_name:
                        type: string
                    email:
                        type: string

        400:
            description: Error with parameters

        502:
            description: Failed to update email in Firebase
        """
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
        new_email = body['email']
        # Keep Firebase auth profile in sync with the app user profile.
        try:
            firebase_auth.update_user(g.user.firebase_user_id, email=new_email)
        except Exception:
            db.session.rollback()
            return jsonify({'error': 'Failed to update email in Firebase'}), 502
        g.user.email = new_email

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
    """
    Delete user account
    ---
    tags:
        - Users
    responses:
        200:
            description: Delete user account
            schema:
                type: object
                properties:
                    message:
                        type: string
                    user_id:
                        type: string
                    is_active:
                        type: boolean
        400:
            description: Error with parameters

        409:
            description: User has already submitted a coach survey
        """
    _, err = _ensure_self(user_id)
    if err:
        return err

    firebase_auth.delete_user(g.user.firebase_user_id)
    g.user.is_active = False
    db.session.commit()

    return jsonify({'message': 'Account deactivated', 'user_id': str(g.user.user_id), 'is_active': False}), 200
