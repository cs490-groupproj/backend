from uuid import UUID

from flask import Blueprint, g, jsonify, request
from firebase_admin import auth
from datetime import datetime, timezone, timedelta

from auth.authentication import require_auth
from auth.util import can_access_admin_endpoint
from models import *

admin_blueprint = Blueprint('admin', __name__)

@admin_blueprint.route('/users/active')
@require_auth
def active_users():
    """
    Get active user counts
    ---
    tags:
        - Admin
    responses:
        200:
            description: Active user counts
            schema:
                type: object
                properties:
                    dau:
                        type: integer
                    wau:
                        type: integer
                    mau:
                        type: integer
    """

    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    now = datetime.now(timezone.utc)
    cutoffs = {
        'dau': now - timedelta(days=1),
        'wau': now - timedelta(weeks=1),
        'mau': now - timedelta(days=30),
    }
    counts = {'dau': 0, 'wau': 0, 'mau': 0}

    page = auth.list_users()
    while page:
        for user in page.users:
            last_sign_in = user.user_metadata.last_sign_in_timestamp
            if not last_sign_in:
                continue
            last_sign_in_dt = datetime.fromtimestamp(
                last_sign_in / 1000, tz=timezone.utc
            )
            for key, cutoff in cutoffs.items():
                if last_sign_in_dt >= cutoff:
                    counts[key] += 1

        page = page.get_next_page()

    return jsonify(counts), 200

@admin_blueprint.route('/users/all')
@require_auth
def all_users():
    """
    Get all users
    ---
    tags:
        - Admin
    paramters:
        - name: limit
          in: path
          required: true
          type: integer
        - name: offset
          in: path
          required: true
          type: integer
    responses:
        200:
            description: All users
            schema:
                type: object
                properties:
                    total_count:
                        type: integer
                    users:
                        type: array
                        items:
                            type: object
                            properties:
                                user_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
                                is_active:
                                    type: boolean
    """
    limit = request.args.get('limit')
    offset = request.args.get('offset')

    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    query = db.session.query(Users).filter(Users.is_active == True).order_by(Users.user_id)

    total = query.count()

    users = query.limit(limit).offset(offset).all()

    return jsonify({
        'total_count': total,
        'users': [{
            'user_id': u.user_id,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'is_active': u.is_active
        } for u in users]
    }), 200

@admin_blueprint.route('/users/ban', methods=['POST'])
@require_auth
def ban_user():
    """
    Ban a user
    ---
    tags:
        - Admin
    paramters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                user_id:
                    type: string
    responses:
        200:
            description: Ban user
            schema:
                type: object
                properties:
                    message:
                        type: string
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401


    user_id = request.json.get('user_id')

    if user_id is None:
        return jsonify({'message': 'user_id missing in request body'}), 400

    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'message': 'Invalid user ID'}), 400

    user = db.session.query(Users).filter(Users.user_id == user_id).first()

    user.is_active = False

    try:
        auth.update_user(
            user.firebase_user_id,
            disabled=True
        )
        auth.revoke_refresh_tokens(user.firebase_user_id)
    except:
        return jsonify({'message': 'User is banned but Firebase has not been deactivated'}), 502

    db.session.query(CoachReports).filter(CoachReports.coach_id == user_id).delete()

    db.session.commit()

    return jsonify({
        'message': 'User banned'
    }), 200


@admin_blueprint.route('/reports')
@require_auth
def get_reports():
    """
    Get coach reports
    ---
    tags:
        - Admin
    paramters:
        - name: limit
          in: path
          required: true
          type: integer
        - name: offset
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get coach reports
            schema:
                type: object
                properties:
                    total_count:
                        type: integer
                    reports:
                        type: array
                        items:
                            type: object
                            properties:
                                coach_report_id:
                                    type: integer
                                coach:
                                    type: object
                                    properties:
                                        coach_id:
                                            type: string
                                        first_name:
                                            type: string
                                        last_name:
                                            type: string
                                        email:
                                            type: string
                                report_message:
                                    type: string
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    limit = request.args.get('limit')
    offset = request.args.get('offset')

    if limit is None or offset is None:
        return jsonify({'message': 'limit and offset are required parameters'}), 400

    query = db.session.query(CoachReports).order_by(CoachReports.coach_report_id.desc())
    count = query.count()
    reports = query.limit(limit).offset(offset).all()

    return jsonify({
        'total_count': count,
        'reports': [{
            'coach_report_id': r.coach_report_id,
            'coach': {
                'coach_id': r.coach_id,
                'first_name': r.coach.first_name,
                'last_name': r.coach.last_name,
                'email': r.coach.email,
            },
            'report_message': r.report_body
        } for r in reports]
    })


@admin_blueprint.route('/reject_report', methods=['POST'])
@require_auth
def reject_report():
    """
    Reject a coach report
    ---
    tags:
        - Admin
    paramters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                coach_report_id:
                type: integer
    responses:
        200:
            description: Reject coach report
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    report_id = request.json.get('coach_report_id')
    if report_id is None:
        return jsonify({'message': 'coach_report_id missing in request body'}), 400

    report = db.session.query(CoachReports).filter(CoachReports.coach_report_id == report_id).first()

    db.session.delete(report)

    return jsonify({
        'message': 'Rejected report'
    }), 200

@admin_blueprint.route('/review_surveys')
@require_auth
def applications():
    """
    Review surveys
    ---
    tags:
        - Admin
    paramters:
        - name: limit
          in: path
          required: true
          type: integer
        - name: offset
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get surveys
            schema:
                type: object
                properties:
                    total_count:
                        type: integer
                    candidates:
                        type: array
                        items:
                            type: object
                            properties:
                                survey_id:
                                    type: integer
                                user_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
                                email:
                                    type: string
                                specialization:
                                    type: string
                                qualifications:
                                    type: string
                                date_submitted:
                                    type: string
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    limit = request.args.get('limit')
    offset = request.args.get('offset')

    if limit is None or offset is None:
        return jsonify({'message': 'limit and offset are required parameters'}), 400

    query = db.session.query(CoachSurveys).order_by(CoachSurveys.date_created.desc())
    count = query.count()
    surveys = query.limit(limit).offset(offset).all()

    return jsonify({
        'total_count': count,
        'candidates': [{
            'survey_id': s.coach_survey_id,
            'user_id': s.user_id,
            'first_name': s.user.first_name,
            'last_name': s.user.last_name,
            'email': s.user.email,
            'specialization': s.specialization,
            'qualifications': s.qualifications,
            'date_submitted': str(s.date_created)
        } for s in surveys]
    })

@admin_blueprint.route('/make_coach', methods=['POST'])
@require_auth
def make_coach():
    """
    Make a user a coach
    ---
    tags:
        - Admin
    paramters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                user_id:
                    type: string
    responses:
        200:
            description: Make coach
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    user_id = request.json.get('user_id')

    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'message': 'Invalid user ID'}), 400

    user = db.session.query(Users).filter(Users.user_id == user_id).first()
    user.is_coach = True
    
    db.session.commit()

    return jsonify({
        'message': 'Lo! This worthy soul hath been raised by sword and sworn into the ancient and honourable company of coaches'
    }), 200

@admin_blueprint.route('/reject_application', methods=['POST'])
@require_auth
def reject_application():
    """
    Reject application
    ---
    tags:
        - Admin
    paramters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                survey_id:
                    type: integer
    responses:
        200:
            description: Get surveys
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Invalid parameters

        404:
            description: Coach survey not found
    """
    if not can_access_admin_endpoint(g.user):
        return jsonify({'message': 'You are not authorized to access this content'}), 401

    survey_id = request.json.get('survey_id')
    if survey_id is None:
        return jsonify({'message': 'survey_id missing in request body'}), 400

    survey = db.session.query(CoachSurveys).filter(CoachSurveys.coach_survey_id == survey_id).first()
    if survey is None:
        return jsonify({'message': 'Survey not found'}), 404

    db.session.delete(survey)
    db.session.commit()

    return jsonify({'message': 'Coach rejected'}), 200