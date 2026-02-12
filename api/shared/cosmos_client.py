import logging
import os

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient

_cosmos_client = None
_container = None
_partition_key_field = None

DATABASE_NAME = "EcoFleetDB"
CONTAINER_NAME = "Telemetry"

def get_cosmos_container():
    """Lazy singleton: crea il CosmosClient via Managed Identity."""
    global _cosmos_client, _container, _partition_key_field
    if _container is None:
        endpoint = os.environ.get("CosmosDBConnectionString__accountEndpoint")
        if endpoint:
            credential = DefaultAzureCredential()
            _cosmos_client = CosmosClient(url=endpoint, credential=credential)
            db = _cosmos_client.get_database_client(DATABASE_NAME)
            _container = db.get_container_client(CONTAINER_NAME)

            # Rileva partition key path
            props = _container.read()
            pk_paths = props.get("partitionKey", {}).get("paths", ["/id"])
            _partition_key_field = pk_paths[0].lstrip("/")  # es. "id" o "vehicle_id"
            logging.info(f"✅ CosmosClient initialized (PK field: {_partition_key_field})")
        else:
            logging.warning("⚠️ CosmosDBConnectionString__accountEndpoint not configured.")
    return _container

def get_partition_key_field():
    """Restituisce il nome del campo usato come partition key."""
    return _partition_key_field or "id"
