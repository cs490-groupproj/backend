import gevent.monkey
gevent.monkey.patch_all()

import os
import traceback
import sys
from flask_socketio import SocketIO

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

    if config_overrides:
        app.config.update(config_overrides)

    DATA_GOV_KEY = os.getenv("DATA_GOV_KEY")

    db.init_app(app)
    socketio.init_app(app, async_mode="gevent")

    app.register_blueprint(client_blueprint, url_prefix='/clients')
    app.register_blueprint(nutrition_blueprint, url_prefix='/nutrition')
    app.register_blueprint(usda_proxy_blueprint, url_prefix='/proxy/usda')
    app.register_blueprint(users_blueprint, url_prefix='/users')
    app.register_blueprint(workouts_blueprint)
    app.register_blueprint(message_blueprint, url_prefix='/messages')
    app.register_blueprint(coach_blueprint, url_prefix='/coaches')

    init_firebase()

    @app.route('/')
    def hello_world():  # put application's code here
        test = (
            db.session.query(ExerciseCategories)
            .all()
        )

        return jsonify([{'name': ec.name} for ec in test]), 200

    @app.route('/authtest')
    @require_auth
    def auth_required():
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

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)
