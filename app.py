import gevent.monkey
gevent.monkey.patch_all()

import os
import traceback
import sys
from flask_socketio import SocketIO
from flasgger import Swagger

from dotenv import load_dotenv
from flask import Flask, jsonify, g
from flask_cors import CORS

from auth.init_firebase import init_firebase
from auth.authentication import require_auth
from models import db, ExerciseCategories

from endpoints.client import client_blueprint
from endpoints.coach import coach_blueprint
from endpoints.message_history import message_blueprint
from endpoints.nutrition import nutrition_blueprint
from endpoints.usda_proxy import usda_proxy_blueprint
from endpoints.users import users_blueprint
from endpoints.workouts import workouts_blueprint
from endpoints.payments import payments_blueprint
from endpoints.admin import admin_blueprint
from endpoints.progress import progress_blueprint


socketio = SocketIO(cors_allowed_origins="*")
import message_sockets # DO NOT REMOVE THIS. It appears unused, but needs to be here for the sockets to register

def create_app(config_overrides=None):

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(base_dir, 'secrets', '.env')
    load_dotenv(dotenv_path)

    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
    # print(os.getenv("DATABASE_URI"))
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SWAGGER"] = {
        'title': 'Optimal API',
        'uiversion': 3,
        'version': '1.0.0'
    }

    if config_overrides:
        app.config.update(config_overrides)

    DATA_GOV_KEY = os.getenv("DATA_GOV_KEY")

    db.init_app(app)
    socketio.init_app(app, async_mode="gevent")

<<<<<<< Updated upstream
    app.register_blueprint(client_blueprint, url_prefix='/clients')
    app.register_blueprint(nutrition_blueprint, url_prefix='/nutrition')
    app.register_blueprint(usda_proxy_blueprint, url_prefix='/proxy/usda')
    app.register_blueprint(users_blueprint, url_prefix='/users')
    app.register_blueprint(workouts_blueprint)
    app.register_blueprint(message_blueprint, url_prefix='/messages')
    app.register_blueprint(coach_blueprint, url_prefix='/coaches')
    app.register_blueprint(payments_blueprint, url_prefix='/payments')
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(progress_blueprint, url_prefix='/progress')
=======
@app.route('/users/me', methods=['GET'])
@require_auth
def get_current_user():
    user = g.user
    return jsonify({
        'user_id': str(user.user_id),
        'firebase_user_id': user.firebase_user_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': g.firebase_user.get('email'),
    }), 200

@app.route('/users/register', methods=['POST'])
@require_auth
def register_user():
    # This endpoint allows registering a user that has authenticated with Firebase
    # but doesn't have a record in the users table yet
    body = request.get_json(silent=True) or {}
    
    firebase_user = g.firebase_user
    firebase_user_id = firebase_user.get('user_id')
    email = firebase_user.get('email')
    
    # Check if user already exists
    existing_user = db.session.query(Users).filter(Users.firebase_user_id == firebase_user_id).first()
    if existing_user:
        # Update existing user if fields are missing
        updated = False
        if not existing_user.email and email:
            existing_user.email = email
            updated = True
        if existing_user.is_coach is None:
            existing_user.is_coach = body.get('is_coach', False)
            updated = True
        if existing_user.is_active is None:
            existing_user.is_active = True
            updated = True
        if not existing_user.first_name:
            existing_user.first_name = body.get('first_name', '')
            updated = True
        if not existing_user.last_name:
            existing_user.last_name = body.get('last_name', '')
            updated = True
        
        if updated:
            db.session.commit()
        
        return jsonify({
            'user_id': str(existing_user.user_id),
            'firebase_user_id': existing_user.firebase_user_id,
            'first_name': existing_user.first_name,
            'last_name': existing_user.last_name,
            'email': existing_user.email,
            'updated': updated,
        }), 200
    else:
        # Create new user
        new_user = Users()
        new_user.firebase_user_id = firebase_user_id
        new_user.first_name = body.get('first_name', '')
        new_user.last_name = body.get('last_name', '')
        new_user.email = email or ''
        new_user.is_coach = body.get('is_coach', False)
        new_user.is_active = True
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'user_id': str(new_user.user_id),
            'firebase_user_id': new_user.firebase_user_id,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'email': new_user.email,
        }), 201
>>>>>>> Stashed changes

    init_firebase()

    @app.route('/')
    def hello_world():  # put application's code here
        """
        Get a list of all exercise categories
        ---
        tags:
            - Testing
        responses:
            200:
                description: List of exercise categories
                schema:
                    type: array
                    items:
                        type: object
                        properties:
                            name:
                                type: string
        """
        test = (
            db.session.query(ExerciseCategories)
            .all()
        )

        return jsonify([{'name': ec.name} for ec in test]), 200

    @app.route('/authtest')
    @require_auth
    def auth_required():
        """
        Get user's email and first name
        ---
        tags:
            - Testing
        responses:
            200:
                description: User's email and first name
                schema:
                    type: object
                    properties:
                        message:
                            type: string
            401:
                description: Unauthorized
        """
        return jsonify({'message': f'You have successfully authenticated, {g.firebase_user.get("email")}. Your name is {g.user.first_name}'}), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'message': 'That resource cannot be found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'message': 'HTTP method is not allowed on that resource'}), 405

    @app.errorhandler(418)
    def im_a_teapot(e):
        return jsonify({'message': 'You have attempted to brew coffee with a teapot. Why?'}), 418

    @app.errorhandler(500)
    def internal_server_error(e):
        tb = traceback.extract_tb(sys.exc_info()[2])[-1]
        return jsonify({
            'message': f'An internal error occurred. Please try again later.',
            'internal_error': traceback.format_exc().splitlines()[-1],
            'location': f'{tb.filename}:{tb.lineno} in {tb.name}'
        }), 500

    Swagger(app)

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)
