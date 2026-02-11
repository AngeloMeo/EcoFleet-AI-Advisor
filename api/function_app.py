import logging
import azure.functions as func
import logging
import json
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
    import hashlib
    # Preparazione documento Cosmos DB
    doc = {
        "id": hashlib.sha256(msg.get_body()).hexdigest(),
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
                    sql_query="Select DISTINCT VALUE c.vehicle_id FROM c",
                    connection="CosmosDBConnectionString")
def get_vehicles(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    logging.info("Richiesta lista veicoli")
    
    vehicles = [doc for doc in documents]

    return func.HttpResponse(json.dumps(vehicles), mimetype="application/json")

@app.route(route="history", auth_level=func.AuthLevel.ANONYMOUS)
@app.cosmos_db_input(arg_name="documents",
                    database_name="EcoFleetDB",
                    container_name="Telemetry",
                    sql_query="Select * FROM c where c.vehicle_id = {Query.vehicleId}",
                    connection="CosmosDBConnectionString")
def get_vehicle_history(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    id = req.params.get("vehicleId")
    logging.info(f"Richiesta storico veicolo {id}")

    if not id:
        return func.HttpResponse("Inserisci un id", status_code=404)
    
    history = [json.loads(doc.to_json()) for doc in documents]
    
    return func.HttpResponse(json.dumps(history), mimetype="application/json")
