import logging
import json
import hashlib
import datetime

import azure.functions as func

from shared.iot_hub import get_iot_registry_manager
from shared.ai_advisor import get_ai_advice

bp = func.Blueprint()

# =============================================================================
# FUNCTION 1: ProcessTelemetry (FAST — nessuna attesa per Gemini)
# Riceve D2C da IoT Hub, salva su Cosmos, invia a SignalR, inoltra ad advice-queue
# =============================================================================
@bp.event_hub_message_trigger(arg_name="event", event_hub_name="%IoTHubEventHubName%", connection="IoTHubEventHubConnectionString", consumer_group="$Default")
@bp.cosmos_db_output(arg_name="outputDocument", database_name="EcoFleetDB", container_name="Telemetry", connection="CosmosDBConnectionString", create_if_not_exists=True)
@bp.generic_output_binding(arg_name="signalRMessages", type="signalR", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
@bp.queue_output(arg_name="adviceQueue", queue_name="advice-queue", connection="AzureStorageQueueConnectionString")
def ProcessTelemetry(event: func.EventHubEvent, outputDocument: func.Out[func.Document], signalRMessages: func.Out[str], adviceQueue: func.Out[str]):
    body = event.get_body().decode('utf-8')
    logging.info(f"📡 D2C Telemetry received from IoT Hub: {body}")
    
    try:
        telemetry = json.loads(body)
    except Exception as e:
        logging.error(f"Error parsing message: {e}")
        return

    speed = telemetry.get("speed", 0)
    rpm = telemetry.get("rpm", 0)
    fuel_level = telemetry.get("fuel_level", 100)
    vehicle_id = telemetry.get("vehicle_id")

    doc_id = hashlib.sha256(event.get_body()).hexdigest()

    # Documento Cosmos DB (senza advice — verrà aggiornato da GenerateAdvice)
    doc = {
        "id": doc_id,
        "vehicle_id": vehicle_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "speed": speed,
        "rpm": rpm,
        "fuel_level": fuel_level,
        "ai_advice": "",
        "alert_level": "INFO",
        "processed_at": datetime.datetime.utcnow().isoformat()
    }

    # 1. Salva su Cosmos DB
    try:
        outputDocument.set(func.Document.from_dict(doc))
        logging.info(f"✅ Telemetry saved to Cosmos: {doc_id}")
    except Exception as e:
        logging.error(f"CRITICAL ERROR saving to Cosmos: {e}")

    # 2. Invia dati IMMEDIATI alla Dashboard via SignalR
    try:
        signalRMessages.set(json.dumps({
            'target': 'newTelemetry',
            'arguments': [doc]
        }))
        logging.info("📡 Telemetry dispatched to SignalR (instant)")
    except Exception as e:
        logging.error(f"Error sending telemetry to SignalR: {e}")

    # 3. Inoltra alla advice-queue per generazione AI asincrona
    try:
        advice_request = {
            "doc_id": doc_id,
            "vehicle_id": vehicle_id,
            "speed": speed,
            "rpm": rpm,
            "fuel_level": fuel_level,
        }
        adviceQueue.set(json.dumps(advice_request))
        logging.info("📨 Forwarded to advice-queue for AI processing")
    except Exception as e:
        logging.error(f"Error forwarding to advice-queue: {e}")


# =============================================================================
# FUNCTION 2: GenerateAdvice (ASYNC — chiama Gemini, poi aggiorna dashboard)
# =============================================================================
@bp.queue_trigger(arg_name="msg", queue_name="advice-queue", connection="AzureStorageQueueConnectionString")
@bp.generic_output_binding(arg_name="signalRMessages", type="signalR", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
def GenerateAdvice(msg: func.QueueMessage, signalRMessages: func.Out[str]):
    try:
        request = json.loads(msg.get_body().decode('utf-8'))
    except Exception as e:
        logging.error(f"Error parsing advice request: {e}")
        return

    doc_id = request.get("doc_id")
    vehicle_id = request.get("vehicle_id")
    speed = request.get("speed", 0)
    rpm = request.get("rpm", 0)
    fuel_level = request.get("fuel_level", 100)

    # 1. Chiama Gemini via LangChain
    result = get_ai_advice(speed, rpm, fuel_level)
    advice = result.advice
    alert_level = result.alert_level
    logging.info(f"🤖 AI Advice for {vehicle_id}: {advice} [{alert_level}]")

    # 2. Aggiorna il documento in Cosmos DB con l'advice
    try:
        from shared.cosmos_client import get_cosmos_container, get_partition_key_field
        container = get_cosmos_container()
        if container:
            pk_field = get_partition_key_field()
            # Leggi il doc esistente, aggiorna i campi advice
            existing = container.read_item(item=doc_id, partition_key=doc_id if pk_field == "id" else vehicle_id)
            existing["ai_advice"] = advice
            existing["alert_level"] = alert_level
            container.upsert_item(existing)
            logging.info(f"✅ Cosmos doc {doc_id} updated with AI advice")
    except Exception as e:
        logging.warning(f"⚠️ Could not update Cosmos doc with advice: {e}")

    # 3. Invia advice alla Dashboard via SignalR (evento separato)
    try:
        signalRMessages.set(json.dumps({
            'target': 'newAdvice',
            'arguments': [{
                "doc_id": doc_id,
                "vehicle_id": vehicle_id,
                "ai_advice": advice,
                "alert_level": alert_level,
            }]
        }))
        logging.info("📡 AI Advice dispatched to SignalR")
    except Exception as e:
        logging.error(f"Error sending advice to SignalR: {e}")

    # 4. Invio C2D Feedback al veicolo
    if vehicle_id:
        registry_manager = get_iot_registry_manager()
        if registry_manager:
            try:
                registry_manager.send_c2d_message(vehicle_id, advice)
                logging.info(f"📤 C2D [{alert_level}] -> {vehicle_id}: {advice}")
            except Exception as e:
                logging.error(f"❌ Failed to send C2D to {vehicle_id}: {e}")


# --- DELETE ENDPOINTS ---

@bp.route(route="telemetry/{vehicleId}", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_vehicle_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella tutti i documenti di un veicolo da Cosmos DB."""
    from shared.cosmos_client import get_cosmos_container, get_partition_key_field

    vehicle_id = req.route_params.get("vehicleId")
    if not vehicle_id:
        return func.HttpResponse("vehicleId richiesto", status_code=400)

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    pk_field = get_partition_key_field()

    try:
        query = f"SELECT c.id, c.{pk_field} FROM c WHERE c.vehicle_id = @vid"
        params = [{"name": "@vid", "value": vehicle_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        deleted = 0
        for item in items:
            container.delete_item(item=item["id"], partition_key=item[pk_field])
            deleted += 1

        logging.info(f"🗑️ Deleted {deleted} docs for {vehicle_id} (PK: {pk_field})")
        return func.HttpResponse(json.dumps({"deleted": deleted}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)


@bp.route(route="telemetry", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_all_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Cancella TUTTI i documenti telemetria da Cosmos DB."""
    from shared.cosmos_client import get_cosmos_container, get_partition_key_field

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse("Cosmos non configurato", status_code=500)

    pk_field = get_partition_key_field()

    try:
        items = list(container.query_items(
            query=f"SELECT c.id, c.{pk_field} FROM c",
            enable_cross_partition_query=True
        ))

        deleted = 0
        for item in items:
            container.delete_item(item=item["id"], partition_key=item[pk_field])
            deleted += 1

        logging.info(f"🗑️ Deleted ALL {deleted} docs (PK: {pk_field})")
        return func.HttpResponse(json.dumps({"deleted": deleted}), mimetype="application/json")
    except Exception as e:
        logging.error(f"Delete all error: {e}")
        return func.HttpResponse(f"Errore: {e}", status_code=500)

