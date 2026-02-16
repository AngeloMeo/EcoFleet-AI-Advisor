import logging
import json

import azure.functions as func

from shared.ai_advisor import get_ai_advice
from shared.cosmos_client import get_cosmos_container, get_partition_key_field
from shared.iot_hub import get_iot_registry_manager

bp = func.Blueprint()

# =============================================================================
# GenerateAdvice (ASYNC — chiama Gemini, poi aggiorna dashboard e veicolo)
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
        container = get_cosmos_container()
        if container:
            pk_field = get_partition_key_field()
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
