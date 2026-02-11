import os
import json
import time
import base64
from azure.storage.queue import QueueClient, TextBase64EncodePolicy, TextBase64DecodePolicy
from azure.core.exceptions import ResourceExistsError

# CONFIGURAZIONE
QUEUE_NAME = "telemetry-queue"

def get_connection_string():
    # Cerca local.settings.json nella cartella ../api/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(current_dir, "..", "api", "local.settings.json")
    
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Non trovo il file settings in: {settings_path}")
    
    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    conn_str = data.get("Values", {}).get("AzureStorageQueueConnectionString")
    if not conn_str or "INCOLLA_QUI" in conn_str:
        raise ValueError("AzureStorageQueueConnectionString è vuota o mock in local.settings.json!")
        
    return conn_str

def send_test_message():
    try:
        CONNECTION_STRING = get_connection_string()
    except Exception as e:
        print(f"❌ Errore Configurazione: {e}")
        return

    print(f"Connecting to queue: {QUEUE_NAME}...")

    try:
        # Configura la client queue con policy Base64 (Richiesto da Azure Functions default)
        queue_client = QueueClient.from_connection_string(
            CONNECTION_STRING, 
            QUEUE_NAME,
            message_encode_policy=TextBase64EncodePolicy(),
            message_decode_policy=TextBase64DecodePolicy()
        )
        
        # Crea la coda se non esiste (utile per il primo avvio)
        try:
            queue_client.create_queue()
            print("Coda creata.")
        except ResourceExistsError:
            print("Coda già esistente.")

        # Dati di prova
        telemetry = {
            "vehicle_id": "TEST-AUTO-69",
            "speed": 165,  # Velocità alta per triggerare l'AI
            "rpm": 3500,
            "fuel_level": 45
        }
        
        message = json.dumps(telemetry)
        queue_client.send_message(message)
        print(f"✅ Messaggio inviato: {message}")
        print("Controlla il terminale di 'func start' per vedere se lo processa!")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    send_test_message()
