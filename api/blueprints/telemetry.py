import logging
import json
import hashlib
import datetime

import azure.functions as func

bp = func.Blueprint()

# =============================================================================
# ProcessTelemetry (FAST — nessuna attesa per Gemini)
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
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc = {
        "id": doc_id,
        "vehicle_id": vehicle_id,
        "timestamp": now,
        "speed": speed,
        "rpm": rpm,
        "fuel_level": fuel_level,
        "ai_advice": "",
        "alert_level": "INFO",
        "processed_at": now
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
