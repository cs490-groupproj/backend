import os

import requests

from auth.authentication import require_auth
from flask import Blueprint, request

usda_proxy_blueprint = Blueprint('proxy_usda', __name__)

BASE_URL = 'https://api.nal.usda.gov/fdc/v1'


@usda_proxy_blueprint.route('/foods/search', methods=['POST'])
@require_auth
def search():
    body = request.get_json()
    endpoint = _build_endpoint('/foods/search')
    response = requests.post(endpoint, json=body)
    return response.json(), response.status_code


@usda_proxy_blueprint.route('/foods/<fdc_id>')
@require_auth
def get_food(fdc_id):
    endpoint = _build_endpoint('/food/' + fdc_id)
    response = requests.get(endpoint)
    return response.json(), response.status_code


def _build_endpoint(path):
    # Do not import app here — app.py imports this module, which would cause a circular import.
    key = os.getenv('DATA_GOV_KEY', '')
    return BASE_URL + path + '?api_key=' + key
