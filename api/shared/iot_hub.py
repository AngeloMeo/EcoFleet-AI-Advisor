import logging
import os

from azure.iot.hub import IoTHubRegistryManager

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
