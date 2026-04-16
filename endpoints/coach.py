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
