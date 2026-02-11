import logging
import os
import json
import hashlib
import datetime

import azure.functions as func
from azure.iot.hub import IoTHubRegistryManager

app = func.FunctionApp()

# --- SINGLETON: IoT Hub Client (riusato tra le invocazioni) ---
_iot_registry_manager = None

def get_iot_registry_manager():
    """Lazy singleton: crea il client una sola volta per processo."""
    global _iot_registry_manager
    if _iot_registry_manager is None:
        conn_str = os.environ.get("IotHubConnectionString")
        if conn_str:
            _iot_registry_manager = IoTHubRegistryManager(conn_str)
            logging.info("✅ IoT Hub Registry Manager initialized (singleton)")
        else:
            logging.warning("⚠️ IotHubConnectionString not configured. C2D feedback disabled.")
    return _iot_registry_manager

@app.route(route="negotiate", auth_level=func.AuthLevel.ANONYMOUS)
@app.generic_input_binding(arg_name="connectionInfo", type="signalRConnectionInfo", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
def negotiate(req: func.HttpRequest, connectionInfo: str) -> func.HttpResponse:
    return func.HttpResponse(connectionInfo)

@app.queue_trigger(arg_name="msg", queue_name="telemetry-queue", connection="AzureStorageQueueConnectionString")
@app.cosmos_db_output(arg_name="outputDocument", database_name="EcoFleetDB", container_name="Telemetry", connection="CosmosDBConnectionString", create_if_not_exists=True)
@app.generic_output_binding(arg_name="signalRMessages", type="signalR", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
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
    # Solo se c'è un advice rilevante (WARN/CRITICAL) per non intasare la rete
    if alert_level in ["WARN", "CRITICAL"] and vehicle_id:
        registry_manager = get_iot_registry_manager()
        if registry_manager:
            try:
                registry_manager.send_c2d_message(vehicle_id, advice)
                logging.info(f"📤 C2D Message sent to {vehicle_id}: {advice}")
            except Exception as e:
                logging.error(f"❌ Failed to send C2D message to {vehicle_id}: {e}")

    # Preparazione documento Cosmos DB
    doc = {
        "id": hashlib.sha256(msg.get_body()).hexdigest(),
        "vehicle_id": vehicle_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "speed": speed,
        "rpm": rpm,
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


@app.route(route="vehicles", auth_level=func.AuthLevel.ANONYMOUS)
@app.cosmos_db_input(arg_name="documents",
                    database_name="EcoFleetDB",
                    container_name="Telemetry",
                    sql_query="SELECT DISTINCT c.vehicle_id FROM c",
                    connection="CosmosDBConnectionString")
def get_vehicles(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    logging.info("Richiesta lista veicoli")
    
    # Ogni doc è {"vehicle_id": "BUS-01"}, estraiamo solo l'ID
    vehicles = [json.loads(doc.to_json())["vehicle_id"] for doc in documents]

    return func.HttpResponse(json.dumps(vehicles), mimetype="application/json")

@app.route(route="history/{vehicleId}", auth_level=func.AuthLevel.ANONYMOUS)
@app.cosmos_db_input(arg_name="documents",
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
