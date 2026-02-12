"""
Test C2D: Invia un messaggio Cloud-to-Device a Bus-01.
Usalo per verificare che l'emulatore riceva i feedback.

COME USARE:
1. In un terminale, lancia: python vehicle_emulator.py
2. In un ALTRO terminale, lancia: python test_c2d.py

Se nell'emulatore vedi "🔔 [Bus-01] 📩 FEEDBACK: ..." allora il C2D funziona.
"""
import os
from azure.iot.hub import IoTHubRegistryManager

conn_str = os.getenv("IOTHUB_SERVICE_CONNECTION_STRING")
if not conn_str:
    print("❌ Setta IOTHUB_SERVICE_CONNECTION_STRING!")
    exit(1)

registry = IoTHubRegistryManager(conn_str)
device_id = "Bus-01"
message = "🧪 TEST C2D: Rallenta immediatamente!"

print(f"📤 Sending C2D to {device_id}: {message}")
registry.send_c2d_message(device_id, message)
print("✅ Sent! Controlla il terminale dell'emulatore.")
