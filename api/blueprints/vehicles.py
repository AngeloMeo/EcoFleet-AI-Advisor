import logging
import json

import azure.functions as func

bp = func.Blueprint()

@bp.route(route="vehicles", auth_level=func.AuthLevel.ANONYMOUS)
@bp.cosmos_db_input(arg_name="documents",
                    database_name="EcoFleetDB",
                    container_name="Telemetry",
                    sql_query="SELECT DISTINCT c.vehicle_id FROM c",
                    connection="CosmosDBConnectionString")
def get_vehicles(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    logging.info("Richiesta lista veicoli")
    
    # Ogni doc è {"vehicle_id": "BUS-01"}, estraiamo solo l'ID
    vehicles = [json.loads(doc.to_json())["vehicle_id"] for doc in documents]

    return func.HttpResponse(json.dumps(vehicles), mimetype="application/json")

@bp.route(route="history/{vehicleId}", auth_level=func.AuthLevel.ANONYMOUS)
@bp.cosmos_db_input(arg_name="documents",
                    database_name="EcoFleetDB",
                    container_name="Telemetry",
                    sql_query="SELECT * FROM c WHERE c.vehicle_id = {vehicleId} ORDER BY c.timestamp DESC OFFSET 0 LIMIT 20",
                    connection="CosmosDBConnectionString")
def get_vehicle_history(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    vehicle_id = req.route_params.get("vehicleId")
    logging.info(f"Richiesta storico veicolo {vehicle_id}")

    if not vehicle_id:
        return func.HttpResponse("Inserisci un id", status_code=404)
    
    history = [json.loads(doc.to_json()) for doc in documents]
    
    return func.HttpResponse(json.dumps(history), mimetype="application/json")
