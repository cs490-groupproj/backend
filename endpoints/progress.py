from anyio.streams import file
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ResourceNotFoundError
from flask import Blueprint, request, g, jsonify
import uuid
from datetime import datetime

from auth.authentication import require_auth
from auth.util import can_access_client_endpoint
from models import *
from storage.azure_blob import get_container_client, generate_sas_url

progress_blueprint = Blueprint('progress_blueprint', __name__)

@progress_blueprint.route('/upload', methods=['POST'])
@require_auth
def upload_progress():
    """
    Upload a progress image
    ---
    tags:
        - Progress Images
    consumes:
        - multipart/form-data
    parameters:
        - name: image
          in: path
          required: true
          type: file
        - name: type
          in: path
          required: true
          type: string
    responses:
        201:
            description: Image uploaded
            schema:
                type: object
                properties:
                    message:
                        type: string
                    url:
                        type: string
        400:
            description: Error with parameters

        502:
            description: Error uploaded to Azure
    """
    file = request.files.get('image')
    type = request.form.get('type')

    if not file:
        return jsonify({'message': 'No file was included in upload.'}), 400

    if type is None or type not in ['BEFORE', 'AFTER']:
        return jsonify({'message': 'Type is required and must be either BEFORE or AFTER'}), 400

    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
    blob_name = f'{str(g.user.user_id)}/{type}/{uuid.uuid4()}.{ext}'

    new_progress = ClientProgress()
    new_progress.user_id = g.user.user_id
    new_progress.blob_name = blob_name
    new_progress.type = type
    new_progress.date_uploaded = datetime.now()

    db.session.add(new_progress)

    try:
        container = get_container_client()
        blob_client = container.get_blob_client(blob_name)
        blob_client.upload_blob(file.read(), overwrite=True)
        db.session.commit()
    except (ResourceNotFoundError, HttpResponseError, ServiceRequestError):
        db.session.rollback()
        return jsonify({'message': 'Failure uploading to Azure'}), 502


    sas_url = generate_sas_url(blob_name, expiry_hours=1)

    return jsonify({
        'message': 'Upload successful',
        'url': sas_url,
    }), 201


@progress_blueprint.route('/', methods=['GET'])
@require_auth
def before_progress():
    """
    Get progress images for a type
    ---
    tags:
        - Progress Images
    parameters:
        - name: user_id
          in: path
          required: true
          type: string
        - name: type
          in: path
          required: true
          type: string
    responses:
        200:
            description: Get progress images for a type
            schema:
                type: object
                properties:
                    total_count:
                        type: integer
                    images:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                type:
                                    type: string
                                uploaded_at:
                                    type: string
                                url:
                                    type: string
        400:
            description: Error with parameters
    """
    user_id = request.args.get('user_id')
    type = request.args.get('type')

    if not user_id:
        return jsonify({'message': 'user_id is required'}), 400

    if not type or type not in ['BEFORE', 'AFTER']:
        return jsonify({'message': 'type is required and must be either BEFORE or AFTER'}), 400

    try:
        user_id = uuid.UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return jsonify({'message': 'Invalid user ID'}), 400

    if not can_access_client_endpoint(g.user, user_id, g.clients_ids):
        return jsonify({'message': 'You are not authorized to access this content.'}), 401

    rows = db.session.query(ClientProgress).filter(ClientProgress.user_id == user_id).filter(ClientProgress.type == type).order_by(ClientProgress.date_uploaded.desc()).all()

    images = []
    for row in rows:
        images.append({
            'id': row.client_progress_id,
            'type': row.type,
            'uploaded_at': row.date_uploaded.isoformat(),
            'url': generate_sas_url(row.blob_name, expiry_hours=1),
        })

    return jsonify({
        'total_count': len(images),
        'images': images
    }), 200


@progress_blueprint.route('/delete', methods=['DELETE'])
@require_auth
def delete():
    """
    Delete progress image
    ---
    tags:
        - Progress Images
    parameters:
        - name: id
          in: path
          required: true
          type: string
    responses:
        200:
            description: Delete progress image
            schema:
                type: object
                properties:
                    message:
                        type: string
        400:
            description: Error with parameters
        404:
            description: Progress entry not found
        502:
            description: Error deleting from Azure
    """
    id = request.args.get('id', type=int)
    if not id:
        return jsonify({'message': 'id is required'}), 400

    entry = db.session.query(ClientProgress).filter(ClientProgress.client_progress_id == id).first()

    if not can_access_client_endpoint(g.user, entry.user_id, g.clients_ids):
        return jsonify({'message': 'You are not authorized to access this content.'}), 401

    if not entry:
        return jsonify({'message': 'Progress entry not found.'}), 404

    try:
        container = get_container_client()
        blob_client = container.get_blob_client(entry.blob_name)
        blob_client.delete_blob()
    except (ResourceNotFoundError):
        pass
    except (HttpResponseError, ServiceRequestError):
        return jsonify({'message': 'Failure deleting from Azure'}), 502

    db.session.delete(entry)
    db.session.commit()

    return jsonify({
        'message': 'Deleted successfully',
    }), 200