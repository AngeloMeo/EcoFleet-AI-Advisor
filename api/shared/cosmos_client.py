import logging
import os

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient

_cosmos_client = None
_container = None

DATABASE_NAME = "EcoFleetDB"
CONTAINER_NAME = "Telemetry"

def get_cosmos_container():
    """Lazy singleton: crea il CosmosClient via Managed Identity."""
    global _cosmos_client, _container
    if _container is None:
        endpoint = os.environ.get("CosmosDBConnectionString__accountEndpoint")
        if endpoint:
            credential = DefaultAzureCredential()
            _cosmos_client = CosmosClient(url=endpoint, credential=credential)
            db = _cosmos_client.get_database_client(DATABASE_NAME)
            _container = db.get_container_client(CONTAINER_NAME)
            logging.info("✅ CosmosClient initialized via Managed Identity")
        else:
            logging.warning("⚠️ CosmosDBConnectionString__accountEndpoint not configured.")
    return _container
