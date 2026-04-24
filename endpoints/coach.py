from datetime import datetime
from uuid import UUID

from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, func

from auth.authentication import require_auth
from models import *
from app import db

coach_blueprint = Blueprint('coach_blueprint', __name__)

def _build_coach_json(coach):

    survey = coach[0].coach_surveys[0] if coach[0].coach_surveys else None
    specialization = survey.specialization if survey else None

    return {
        'coach_user_id': coach[0].user_id,
        'first_name': coach[0].first_name,
        'last_name': coach[0].last_name,
        'coach_cost': coach[0].coach_cost,
        'avg_rating': coach[1],
        'certifications': coach[0].certifications,
        'qualifications': coach[0].qualifications,
        'is_exercise_specialization': specialization in ('EXERCISE', 'BOTH'),
        'is_nutrition_specialization': specialization in ('NUTRITION', 'BOTH'),
    }

@coach_blueprint.route('/search')
@require_auth
def search():
    """
    Search coaches
    ---
    tags:
        - Coaches
    parameters:
        - name: limit
          in: path
          required: true
          type: integer
        - name: offset
          in: path
          required: true
          type: integer
        - name: query
          in: path
          required: false
          type: string
    responses:
        200:
            description: Get coaches based on search query, or all coaches if blank
            schema:
                type: object
                properties:
                    total_results:
                        type: integer
                    coaches:
                        type: array
                        items:
                            type: object
                            properties:
                                coach_user_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
                                coach_cost:
                                    type: integer
                                avg_rating:
                                    type: integer
                                is_exercise_specialization:
                                    type: boolean
                                is_nutrition_specialization:
                                    type: boolean
        400:
            description: Error with parameters
    """
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)
    query = request.args.get('query')

    if limit is None or offset is None:
        return jsonify({'message': 'limit and offset parameters must be integers included in URL'}), 400

    avg_ratings = db.session.query(CoachReviews.coach_id, func.avg(CoachReviews.rating).label('avg_rating'))\
        .group_by(CoachReviews.coach_id) \
        .subquery()

    coaches = db.session.query(Users, func.coalesce(avg_ratings.c.avg_rating, 5)) \
        .outerjoin(avg_ratings, Users.user_id == avg_ratings.c.coach_id) \
        .join(CoachSurveys) \
        .filter(Users.is_active == True) \
        .filter(Users.is_coach == True) \
        .order_by(func.coalesce(avg_ratings.c.avg_rating, 0).desc())


    if query is not None:
        terms = query.split(' ')
        filters = []

        for t in terms:
            filters.append(
                or_(
                    Users.first_name.ilike(f'%{t}%'),
                    Users.last_name.ilike(f'%{t}%')
                )
            )

        coaches = coaches.filter(or_(*filters))

        total_results = coaches.count()

        coaches = coaches.offset(offset).limit(limit).all()

        return jsonify({
            'total_results': total_results,
            'coaches': [_build_coach_json(c) for c in coaches]
        })
    else:
        total_results = coaches.count()
        coaches = coaches.offset(offset).limit(limit).all()
        return jsonify({
            'total_results': total_results,
            'coaches': [_build_coach_json(c) for c in coaches]
        })

@coach_blueprint.route('/clients')
@require_auth
def my_clients():
    """
    Get clients for the logged in coach
    ---
    tags:
        - Coaches
    responses:
        200:
            description: Get clients for a logged in coach
            schema:
                type: object
                properties:
                    clients:
                        type: array
                        items:
                            type: object
                            properties:
                                client_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
    """
    relationships = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == g.user.user_id).all()

    return jsonify({
        'clients': [{
            'client_id': r.client.user_id,
            'first_name': r.client.first_name,
            'last_name': r.client.last_name
        } for r in relationships]
    })

@coach_blueprint.route('/<coach_id>/request', methods=['POST'])
@require_auth
def request_coach(coach_id):
    """
    Request a coach
    ---
    tags:
        - Coaches
    responses:
        201:
            description: Request a coach
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Error with parameters

        404:
            description: Coach does not exist
    """
    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'coach_id parameter is invalid'}), 400

    coach = db.session.query(Users).filter(Users.user_id == coach_id).filter(Users.is_coach == True).filter(Users.is_active == True).first()
    if coach is None:
        return jsonify({'message': 'coach does not exist'}), 404

    client_billing = db.session.query(ClientBilling).filter(ClientBilling.client_id == g.user.user_id)

    if client_billing is None:
        return jsonify({'message': 'client billing does not exist'}), 404

    coach_request = CoachRequests()
    coach_request.coach_id = coach_id
    coach_request.client_id = g.user.user_id

    db.session.add(coach_request)
    db.session.commit()

    return jsonify({'message': 'Coach requested'}), 201


@coach_blueprint.route('/<coach_id>/fire', methods=['DELETE'])
@require_auth
def fire_coach(coach_id):
    """
    Fire coach
    ---
    tags:
        - Coaches
    responses:
        200:
            description: Get coaches based on search query, or all coaches if blank
            schema:
                type: object
                properties:
                    total_results:
                        type: integer
                    coaches:
                        type: array
                        items:
                            type: object
                            properties:
                                coach_user_id:
                                    type: string
                                first_name:
                                    type: string
                                last_name:
                                    type: string
                                coach_cost:
                                    type: integer
                                avg_rating:
                                    type: integer
                                is_exercise_specialization:
                                    type: boolean
                                is_nutrition_specialization:
                                    type: boolean
        400:
            description: Error with parameters

        404:
            description: Client/Coach relationship does not exist
    """
    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'coach_id parameter is invalid'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.client_id == g.user.user_id).filter(ClientCoaches.coach_id == coach_id).first()

    if relationship is None:
        return jsonify({'message': 'Relationship does not exist'}), 404
    if relationship.client_billing:
        db.session.delete(relationship.client_billing)
    db.session.delete(relationship)
    db.session.commit()

    return jsonify({'message': 'Coach fired'}), 200

@coach_blueprint.route('/requests')
@require_auth
def get_coach_requests():
    """
    Get all requests for logged in coach
    ---
    tags:
        - Coaches
    parameters:
        - name: limit
          in: path
          required: true
          type: string
        - name: offset
          in: path
          required: true
          type: integer
    responses:
        201:
            description: Request a coach
            schema:
                type: object
                properties:
                    total_results:
                        type: integer
                    requests:
                        type: array
                        items:
                            type: object
                            properties:
                                total_results:
                                    type: integer
                                client:
                                    type: object
                                    properties:
                                        client_id:
                                            type: string
                                        client_first_name:
                                            type: string
                                        client_last_name:
                                            type: string
        400:
            description: Error with parameters

        401:
            description: User is not a coach
    """

    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    if limit is None or offset is None:
        return jsonify({'message': 'limit and offset parameters must be integers included in URL'}), 400

    if not g.user.is_coach:
        return jsonify({'message': 'You are not a coach'}), 401

    query = db.session.query(CoachRequests).filter(CoachRequests.coach_id == g.user.user_id)

    total_results = query.count()
    requests = query.order_by(CoachRequests.coach_request_id.desc()).offset(offset).limit(limit).all()

    return jsonify({
        'total_results': total_results,
        'requests': [{
            'request_id': r.coach_request_id,
            'client': {
                'client_id': r.client_id,
                'client_first_name': r.client.first_name,
                'client_last_name': r.client.last_name,
            }
        } for r in requests]
    })

@coach_blueprint.route('/requests/<int:request_id>/accept', methods=['POST'])
@require_auth
def accept_coach_request(request_id):
    """
    Accept coach request
    ---
    tags:
        - Coaches
    responses:
        201:
            description: Accept coach request
            schema:
                type: object
                properties:
                    message:
                        type: string
        404:
            description: Request does not exist
    """
    coach_request = db.session.query(CoachRequests).filter(CoachRequests.coach_request_id == request_id).first()
    if coach_request is None:
        return jsonify({'message': 'Request does not exist'}), 404

    if coach_request.coach_id != g.user.user_id:
        return jsonify({'message': 'You are not authorized to modify this content'}), 401

    client_billing = db.session.query(ClientBilling).filter(ClientBilling.client_id == coach_request.client_id).first()
    if client_billing is None:
        return jsonify({'message': 'Client billing does not exist'}), 404


    relationship = ClientCoaches()
    relationship.coach_id = coach_request.coach_id
    relationship.client_id = coach_request.client_id
    relationship.client_billing_id = client_billing.client_billing_id
    relationship.paired_date = datetime.now()

    db.session.add(relationship)
    db.session.delete(coach_request)
    db.session.commit()

    return jsonify({'message': 'Coach request accepted'}), 201

@coach_blueprint.route('/requests/<int:request_id>/reject', methods=['POST'])
@require_auth
def reject_coach_request(request_id):
    """
    Reject coach request
    ---
    tags:
        - Coaches
    responses:
        201:
            description: Reject coach request
            schema:
                type: object
                properties:
                    message:
                        type: string
        404:
            description: Request does not exist
    """
    coach_request = db.session.query(CoachRequests).filter(CoachRequests.coach_request_id == request_id).first()
    if coach_request is None:
        return jsonify({'message': 'Request does not exist'}), 404

    if coach_request.coach_id != g.user.user_id:
        return jsonify({'message': 'You are not authorized to modify this content'}), 401

    db.session.delete(coach_request)
    db.session.commit()
    return jsonify({'message': 'Coach request rejected'}), 200


@coach_blueprint.route('/remove_client', methods=['POST'])
@require_auth
def remove_client():
    """
    Remove client
    ---
    tags:
        - Coaches
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                client_id:
                    type: string
    responses:
        200:
            description: Remove a client
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Error with parameters

        404:
            description: Client/Coach relationship does not exist
    """
    client_id = request.json.get('client_id')

    if client_id is None:
        return jsonify({'message': 'Client id parameter is invalid'}), 400

    try:
        client_id = UUID(client_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'Client id parameter is invalid'}), 400

    if client_id not in g.user.clients_ids:
        return jsonify({'message': 'User does not coach client'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.client_id == client_id).filter(ClientCoaches.coach_id == g.user.user_id).all()
    if relationship is None:
        return jsonify({'message': 'Relationship does not exist'}), 404

    db.session.delete(relationship.client_billing)
    db.session.delete(relationship)
    db.session.commit()

    return jsonify({'message': 'Client removed'}), 200


@coach_blueprint.route('/<coach_id>/review', methods=['PUT'])
@require_auth
def review_coach(coach_id):
    """
    Leave a review for a coach
    ---
    tags:
        - Coaches
    parameters:
      - name: body
        in: body
        required: true
        schema:
            type: object
            properties:
                rating:
                    type: integer
    responses:
        201:
            description: Request a coach
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Error with parameters
    """
    rating = request.json.get('rating')
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({'message': 'Rating must be a number'}), 400
    if rating < 0 or rating > 10:
        return jsonify({'message': 'Rating parameter is invalid'}), 400
    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'Coach id parameter is invalid'}), 400
    
    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == coach_id).filter(ClientCoaches.client_id == g.user.user_id).first()

    if not relationship:
        return jsonify({'message': 'You cannot review a coach you don\'t have a relationship with'}), 400

    reviews = db.session.query(CoachReviews).filter(CoachReviews.coach_id == coach_id).filter(CoachReviews.left_by_user_id == g.user.user_id).first()

    if not reviews:
        review = CoachReviews()
        review.coach_id = coach_id
        review.left_by_user_id = g.user.user_id
        review.rating = rating
        db.session.add(review)
    else:
        review = reviews
        review.rating = rating

    db.session.commit()

    return jsonify({'message': 'Review added or modified'}), 200


@coach_blueprint.route('/<coach_id>/report', methods=['POST'])
@require_auth
def report_coach(coach_id):
    """
        Report a coach
        ---
        tags:
            - Coaches
        parameters:
          - name: body
            in: body
            required: true
            schema:
                type: object
                properties:
                    report_body:
                        type: string
        responses:
            201:
                description: Request a coach
                schema:
                    type: object
                    properties:
                        message:
                            type: string
            400:
                description: Error with parameters
        """
    report_body = request.json.get('report_body')
    if not report_body:
        return jsonify({'message': 'Report body parameter must not be null'}), 400

    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'Coach id parameter is invalid'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == coach_id).filter(
        ClientCoaches.client_id == g.user.user_id).first()

    if not relationship:
        return jsonify({'message': 'You cannot report a coach you don\'t have a relationship with'}), 400

    report = CoachReports()
    report.coach_id = coach_id
    report.left_by_user_id = g.user.user_id
    report.report_body = report_body
    report.submitted_datetime = datetime.now()
    db.session.add(report)
    db.session.commit()

    return jsonify({'message': 'Report created'}), 201
