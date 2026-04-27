from uuid import UUID
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_, func
from models import CoachReviews, Users, Exercises, CoachSurveys
from sqlalchemy.orm import joinedload
from app import db

visitor_blueprint = Blueprint('visitor_blueprint', __name__)

def _build_coach_json(coach):

    survey = coach[0].coach_surveys[0] if coach[0].coach_surveys else None

    specialization = survey.specialization if survey else None
    qualifications = survey.qualifications if survey else None

    return {
        'first_name': coach[0].first_name,
        'last_name': coach[0].last_name,
        'avg_rating': coach[1],
        'qualifications': qualifications,
        'is_exercise_specialization': specialization in ('EXERCISE', 'BOTH'),
        'is_nutrition_specialization': specialization in ('NUTRITION', 'BOTH'),
    }

@visitor_blueprint.route('/top_coaches')
def search():
    """
    Search for top coaches
    ---
    tags:
        - Visitors
    parameters:
        - name: limit
          in: path
          required: true
          type: integer
    responses:
        200:
            description: Get coaches based on query
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
                                first_name:
                                    type: string
                                last_name:
                                    type: string
                                avg_rating:
                                    type: integer
                                qualifications:
                                    type: string
                                is_exercise_specialization:
                                    type: boolean
                                is_nutrition_specialization:
                                    type: boolean
        400:
            description: Error with parameters
    """
    limit = request.args.get('limit', type=int)

    if limit is None:
        return jsonify({'message': 'limit parameter must be an integer included in URL'}), 400

    avg_ratings = db.session.query(CoachReviews.coach_id,
        func.avg(CoachReviews.rating).label('avg_rating'))\
        .group_by(CoachReviews.coach_id) \
        .subquery()

    coaches = db.session.query(Users, func.coalesce(avg_ratings.c.avg_rating, 0)) \
        .outerjoin(avg_ratings, Users.user_id == avg_ratings.c.coach_id) \
        .join(CoachSurveys, CoachSurveys.user_id == Users.user_id) \
        .filter(Users.is_active == True) \
        .filter(Users.is_coach == True) \
        .order_by(func.coalesce(avg_ratings.c.avg_rating, 0).desc())

    total_results = coaches.count()
    coaches = coaches.limit(limit).all()
    return jsonify({
        'total_results': total_results,
        'coaches': [_build_coach_json(c) for c in coaches]
    })
    
