import azure.functions as func
import logging
import json
import uuid
import datetime

app = func.FunctionApp()

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

    # --- MOCK AI LOGIC (Finché Azure OpenAI non è disponibile) ---
    speed = telemetry.get("speed", 0)
    rpm = telemetry.get("rpm", 0)
    
    advice = "Guida ottimale. Continua così!"
    if rpm > 3000:
        advice = "Giri troppo alti! Cambia marcia per risparmiare carburante."
    elif speed > 130:
        advice = "Stai superando i limiti. Rallenta per sicurezza e consumi."
    elif speed < 10 and rpm > 1000:
        advice = "Sei fermo o quasi. Spegni il motore se la sosta è lunga."
        
    logging.info(f"AI Mock Advice: {advice}")
    # -------------------------------------------------------------

    # Preparazione documento Cosmos DB
    doc = {
        "id": str(uuid.uuid4()),
        "vehicle_id": telemetry.get("vehicle_id", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "speed": speed,
        "rpm": rpm,
        "ai_advice": advice,
        "processed_at": datetime.datetime.utcnow().isoformat()
    }

    # Output su Cosmos DB
    try:
        outputDocument.set(func.Document.from_dict(doc))
        logging.info(f"✅ Document saved to Cosmos DB: {doc['id']}")
    except Exception as e:
        logging.error(f"CRITICAL ERROR Saving to Cosmos DB: {e}")

    # Output su SignalR (Real-time Dashboard)
    try:
        signalRMessages.set(json.dumps({
            'target': 'newMessage',
            'arguments': [doc]
        }))
        logging.info("📡 Telemetry dispatched to SignalR")
    except Exception as e:
        logging.error(f"Error sending to SignalR: {e}")
