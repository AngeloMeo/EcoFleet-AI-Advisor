import logging
import json
import hashlib
import datetime

import azure.functions as func

from shared.iot_hub import get_iot_registry_manager

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", queue_name="telemetry-queue", connection="AzureStorageQueueConnectionString")
@bp.cosmos_db_output(arg_name="outputDocument", database_name="EcoFleetDB", container_name="Telemetry", connection="CosmosDBConnectionString", create_if_not_exists=True)
@bp.generic_output_binding(arg_name="signalRMessages", type="signalR", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
def ProcessTelemetry(msg: func.QueueMessage, outputDocument: func.Out[func.Document], signalRMessages: func.Out[str]):
    logging.info(f"🚀 TRIGGERED (V2 Model)! Message body: {msg.get_body().decode('utf-8')}")
    
    try:
        body = msg.get_body().decode('utf-8')
        telemetry = json.loads(body)
    except Exception as e:
        logging.error(f"Error parsing message: {e}")
        return

    # --- REAL AI LOGIC & FEEDBACK LOOP ---
    speed = telemetry.get("speed", 0)
    rpm = telemetry.get("rpm", 0)
    fuel_level = telemetry.get("fuel_level", 100)
    vehicle_id = telemetry.get("vehicle_id")
    
    advice = "Guida ottimale. Continua così!"
    alert_level = "INFO" # INFO, WARN, CRITICAL

    if rpm > 3000:
        advice = "Giri troppo alti! Cambia marcia per risparmiare carburante."
        alert_level = "WARN"
    elif speed > 130:
        advice = "Stai superando i limiti. Rallenta per sicurezza e consumi."
        alert_level = "CRITICAL"
    elif speed < 10 and rpm > 1000:
        advice = "Sei fermo o quasi. Spegni il motore se la sosta è lunga."
        alert_level = "WARN"
        
    logging.info(f"AI Advice: {advice} [{alert_level}]")

    # Invio Feedback al Device (C2D) via IoT Hub
    # Invia SEMPRE il feedback al veicolo
    if vehicle_id:
        registry_manager = get_iot_registry_manager()
        if registry_manager:
            try:
                registry_manager.send_c2d_message(vehicle_id, advice)
                logging.info(f"📤 C2D [{alert_level}] -> {vehicle_id}: {advice}")
            except Exception as e:
                logging.error(f"❌ Failed to send C2D to {vehicle_id}: {e}")

    # Preparazione documento Cosmos DB
    doc = {
        "id": hashlib.sha256(msg.get_body()).hexdigest(),
        "vehicle_id": vehicle_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "speed": speed,
        "rpm": rpm,
        "fuel_level": fuel_level,
        "ai_advice": advice,
        "alert_level": alert_level,
        "processed_at": datetime.datetime.utcnow().isoformat()
    }

    # Output su Cosmos DB
    try:
        outputDocument.set(func.Document.from_dict(doc))
        logging.info(f"✅ Document saved to Cosmos DB: {doc['id']}")
    except Exception as e:
        logging.error(f"CRITICAL ERROR Saving to Cosmos DB: {e}")

    # Output su SignalR (Real-time Dashboard) (pub-sub)
    try:
        signalRMessages.set(json.dumps({
            'target': 'newMessage',
            'arguments': [doc]
        }))
        logging.info("📡 Telemetry dispatched to SignalR")
    except Exception as e:
        logging.error(f"Error sending to SignalR: {e}")


# --- DELETE ENDPOINTS ---

@bp.route(route="telemetry/{vehicleId}", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_vehicle_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella tutti i documenti di un veicolo da Cosmos DB."""
    from shared.cosmos_client import get_cosmos_container

    vehicle_id = req.route_params.get("vehicleId")
    if not vehicle_id:
        return func.HttpResponse("vehicleId richiesto", status_code=400)

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    try:
        query = "SELECT c.id FROM c WHERE c.vehicle_id = @vid"
        params = [{"name": "@vid", "value": vehicle_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        for item in items:
            container.delete_item(item=item["id"], partition_key=item["id"])

        logging.info(f"🗑️ Deleted {len(items)} docs for {vehicle_id}")
        return func.HttpResponse(json.dumps({"deleted": len(items)}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)


@bp.route(route="telemetry", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_all_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella TUTTI i documenti telemetria da Cosmos DB."""
    from shared.cosmos_client import get_cosmos_container

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    try:
        items = list(container.query_items(query="SELECT c.id FROM c", enable_cross_partition_query=True))

        for item in items:
            container.delete_item(item=item["id"], partition_key=item["id"])

        logging.info(f"🗑️ Deleted ALL {len(items)} docs")
        return func.HttpResponse(json.dumps({"deleted": len(items)}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete all error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)
