import logging
import json

import azure.functions as func

from shared.cosmos_client import get_cosmos_container, get_partition_key_field

bp = func.Blueprint()


# --- Helper condiviso per cancellazione documenti ---

def _delete_documents(container, pk_field, query, params=None):
    """Esegue una query e cancella tutti i documenti trovati. Restituisce il conteggio."""
    items = list(container.query_items(
        query=query,
        parameters=params or [],
        enable_cross_partition_query=True
    ))
    for item in items:
        container.delete_item(item=item["id"], partition_key=item[pk_field])
    return len(items)


# --- DELETE ENDPOINTS ---

@bp.route(route="telemetry/{vehicleId}", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_vehicle_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella tutti i documenti di un veicolo da Cosmos DB."""
    vehicle_id = req.route_params.get("vehicleId")
    if not vehicle_id:
        return func.HttpResponse("vehicleId richiesto", status_code=400)

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    pk_field = get_partition_key_field()

    try:
        deleted = _delete_documents(
            container, pk_field,
            query=f"SELECT c.id, c.{pk_field} FROM c WHERE c.vehicle_id = @vid",
            params=[{"name": "@vid", "value": vehicle_id}]
        )
        logging.info(f"🗑️ Deleted {deleted} docs for {vehicle_id} (PK: {pk_field})")
        return func.HttpResponse(json.dumps({"deleted": deleted}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)


@bp.route(route="telemetry", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_all_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella TUTTI i documenti telemetria da Cosmos DB."""
    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    pk_field = get_partition_key_field()

    try:
        deleted = _delete_documents(
            container, pk_field,
            query=f"SELECT c.id, c.{pk_field} FROM c"
        )
        logging.info(f"🗑️ Deleted ALL {deleted} docs (PK: {pk_field})")
        return func.HttpResponse(json.dumps({"deleted": deleted}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete all error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)
