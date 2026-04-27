from datetime import datetime, timedelta, timezone
import os
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

CONTAINER_NAME = "progress-images"

def get_blob_service_client():
    connection_string = os.getenv('AZURE_BLOB_CONNECTION_STRING')
    return BlobServiceClient.from_connection_string(connection_string)

def get_container_client():
    return get_blob_service_client().get_container_client(CONTAINER_NAME)

def generate_sas_url(blob_name, expiry_hours):
    blob_service_client = get_blob_service_client()

    account_name = blob_service_client.account_name
    account_key = blob_service_client.credential.account_key

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=CONTAINER_NAME,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    )

    return f'https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas_token}'