import os

import requests

from auth.authentication import require_auth
from flask import Blueprint, request

usda_proxy_blueprint = Blueprint('proxy_usda', __name__)

BASE_URL = 'https://api.nal.usda.gov/fdc/v1'

@usda_proxy_blueprint.route('/foods/search', methods=['POST'])
@require_auth
def search():
    """
    Search USDA FDC API
    ---
    tags:
        - USDA Proxy
    externalDocs:
        description: USDA Food Data Central Docs
        url: https://app.swaggerhub.com/apis/fdcnal/food-data_central_api/1.0.1
    """
    body = request.get_json()
    endpoint = _build_endpoint('/foods/search')
    response = requests.post(endpoint, json=body)
    return response.json(), response.status_code


@usda_proxy_blueprint.route('/foods/<fdc_id>')
@require_auth
def get_food(fdc_id):
    """
    Get Food from USDA FDC API
    ---
    tags:
        - USDA Proxy
    externalDocs:
        description: USDA Food Data Central Docs
        url: https://app.swaggerhub.com/apis/fdcnal/food-data_central_api/1.0.1
    """
    endpoint = _build_endpoint('/food/' + fdc_id)
    response = requests.get(endpoint)
    return response.json(), response.status_code



def _build_endpoint(path):
    key = os.getenv("DATA_GOV_KEY", "")
    return BASE_URL + path + "?api_key=" + key

