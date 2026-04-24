from flask import Blueprint, g, request, jsonify
from datetime import datetime
from models import *

from auth.authentication import require_auth

def _create_billing_object(json, user):
    try:
        billing = ClientBilling()
        billing.client_id = user.user_id
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

def _update_billing_object(billing, json):
    try:
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

payments_blueprint = Blueprint('payments', __name__)

@payments_blueprint.route('/', methods=['PUT'])
@require_auth
def add_payment():
    """
    Add/Update a payment method
    ---
    tags:
        - Payments
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            card_number:
              type: string
            card_exp_month:
              type: integer
            card_exp_year:
              type: integer
            card_security_number:
              type: integer
            card_name:
              type: string
            card_address:
              type: string
            card_address_2:
              type: string
            card_city:
              type: string
            card_postcode:
              type: string
    responses:
        200:
            description: Update a payment method
            schema:
                type: object
                properties:
                    message:
                        type: string
        201:
            description: Add a payment method
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Error with parameters
    """

    user = g.user

    billing = db.session.query(ClientBilling).filter(ClientBilling.client_id == user.user_id).first()

    if not billing:
        data = request.json
        billing = _create_billing_object(data, user)

        db.session.add(billing)
        db.session.commit()

        return jsonify({
            'message': 'Billing information saved'
        }), 201

    else:
        data = request.json
        _update_billing_object(billing, data)

        db.session.commit()

        return jsonify({'message': 'Billing updated successfully'}), 200
