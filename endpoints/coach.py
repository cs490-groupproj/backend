from datetime import datetime
from uuid import UUID

from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, func

from auth.authentication import require_auth
from models import *
from app import db

coach_blueprint = Blueprint('coach_blueprint', __name__)

def _build_coach_json(coach):
    return {
        'coach_user_id': coach[0].user_id,
        'first_name': coach[0].first_name,
        'last_name': coach[0].last_name,
        'coach_cost': coach[0].coach_cost,
        'avg_rating': coach[1],
        'is_exercise_specialization': coach[0].coach_specializations.exercise,
        'is_nutrition_specialization': coach[0].coach_specializations.nutrition
    }

def _create_billing_object(json):
    try:
        billing = ClientBilling()
        billing.card_number = json['card_number']
        billing.card_exp_month = json['card_exp_month']
        billing.card_exp_year = json['card_exp_year']
        billing.card_security_number = json['card_security_number']
        billing.card_name = json['card_name']
        billing.card_address_1 = json['card_address']
        billing.card_address_2 = json['card_address_2'] or None
        billing.card_city = json['card_city']
        billing.card_postcode = json['card_postcode']
        billing.renew_day_number = datetime.now().day
    except (KeyError, TypeError, ValueError):
        return None

    return billing

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
        .join(CoachSpecializations) \
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
    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'coach_id parameter is invalid'}), 400

    coach = db.session.query(Users).filter(Users.user_id == coach_id).filter(Users.is_coach == True).filter(Users.is_active == True).first()
    if coach is None:
        return jsonify({'message': 'coach does not exist'}), 404

    data = request.json
    billing = _create_billing_object(data)

    if billing is None:
        return jsonify({'message': 'billing is invalid not exist'}), 400

    db.session.add(billing)
    db.session.flush()

    coach_request = CoachRequests()
    coach_request.coach_id = coach_id
    coach_request.client_id = g.user.user_id
    coach_request.client_billing_id = billing.client_billing_id

    db.session.add(coach_request)
    db.session.commit()

    return jsonify({'message': 'Coach requested'}), 201


@coach_blueprint.route('/<coach_id>/fire', methods=['POST'])
@require_auth
def fire_coach(coach_id):

    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'coach_id parameter is invalid'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.client_id == g.user.user_id).filter(ClientCoaches.coach_id == coach_id).first()

    if relationship is None:
        return jsonify({'message': 'Relationship does not exist'}), 404

    db.session.delete(relationship.client_billing)
    db.session.delete(relationship)
    db.session.commit()

    return jsonify({'message': 'Coach fired'}), 200

@coach_blueprint.route('/requests')
@require_auth
def get_coach_requests():

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

    coach_request = db.session.query(CoachRequests).filter(CoachRequests.coach_request_id == request_id).first()
    if coach_request is None:
        return jsonify({'message': 'Request does not exist'}), 404

    if coach_request.coach_id != g.user.user_id:
        return jsonify({'message': 'You are not authorized to modify this content'}), 401


    relationship = ClientCoaches()
    relationship.coach_id = coach_request.coach_id
    relationship.client_id = coach_request.client_id
    relationship.client_billing_id = coach_request.client_billing_id
    relationship.paired_date = datetime.now()

    db.session.add(relationship)
    db.session.delete(coach_request)
    db.session.commit()

    return jsonify({'message': 'Coach request accepted'}), 201

@coach_blueprint.route('/requests/<int:request_id>/reject', methods=['POST'])
@require_auth
def reject_coach_request(request_id):
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
    rating = request.json.get('rating')
    if rating is None or rating < 0 or rating > 10:
        return jsonify({'message': 'Rating parameter is invalid'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == coach_id).filter(ClientCoaches.client_id == g.user.user_id).all()

    if relationship is None:
        return jsonify({'message': 'You cannot review a coach you don\'t have a relationship with'}), 400

    reviews = db.session.query(CoachReviews).filter(CoachReviews.coach_id == coach_id).filter(CoachReviews.left_by_user_id == g.user.user_id).all()

    if reviews is None:
        review = CoachReviews()
        review.coach_id = coach_id
        review.left_by_user_id = g.user.user_id
        review.rating = rating
        db.session.add(review)
    else:
        review = reviews[0]
        review.rating = rating

    db.session.commit()

    return jsonify({'message': 'Review added or modified'}), 201


@coach_blueprint.route('/<coach_id>/report', methods=['POST'])
@require_auth
def report_coach(coach_id):

    report_body = request.json.get('report_body')
    if report_body is None or report_body:
        return jsonify({'message': 'Report body parameter must not be null'}), 400

    try:
        coach_id = UUID(coach_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'Coach id parameter is invalid'}), 400

    relationship = db.session.query(ClientCoaches).filter(ClientCoaches.coach_id == coach_id).filter(
        ClientCoaches.client_id == g.user.user_id).all()

    if relationship is None:
        return jsonify({'message': 'You cannot report a coach you don\'t have a relationship with'}), 400

    report = CoachReports()
    report.coach_id = coach_id
    report.left_by_user_id = g.user.user_id
    report.report_body = report_body
    report.submitted_datetime = datetime.now()
    db.session.add(report)
    db.session.commit()

    return jsonify({'message': 'Report created'}), 201
