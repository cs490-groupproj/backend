from flask import Flask, jsonify, g
from flask_cors import CORS

from auth.init_firebase import init_firebase
from auth.authentication import require_auth

app = Flask(__name__)

init_firebase()

CORS(app)

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/authtest')
@require_auth
def auth_required():
    return jsonify({'message': f'You have successfully authenticated, {g.user.get("email")}'}), 200


if __name__ == '__main__':
    app.run()
