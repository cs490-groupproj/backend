import os
from flask_socketio import SocketIO

from dotenv import load_dotenv
from flask import Flask, jsonify, g
from flask_cors import CORS

from auth.init_firebase import init_firebase
from auth.authentication import require_auth
from models import db, ExerciseCategories

from endpoints.client import client_blueprint
from endpoints.message_history import message_blueprint
from endpoints.nutrition import nutrition_blueprint
from endpoints.usda_proxy import usda_proxy_blueprint

base_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_dir, 'secrets', '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*")
import message_sockets # DO NOT REMOVE THIS. It appears unused, but needs to be here for the sockets to register

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
# print(os.getenv("DATABASE_URI"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

DATA_GOV_KEY = os.getenv("DATA_GOV_KEY")

db.init_app(app)

app.register_blueprint(client_blueprint, url_prefix='/clients')
app.register_blueprint(nutrition_blueprint, url_prefix='/nutrition')
app.register_blueprint(usda_proxy_blueprint, url_prefix='/proxy/usda')
app.register_blueprint(message_blueprint, url_prefix='/messages')

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


if __name__ == '__main__':
    socketio.run(app, debug=True)
