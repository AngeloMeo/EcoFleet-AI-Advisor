import logging
import os

from azure.identity import DefaultAzureCredential
from azure.iot.hub import IoTHubRegistryManager

_iot_registry_manager = None

def get_iot_registry_manager():
    """Lazy singleton: crea il client una sola volta per processo (RBAC)."""
    global _iot_registry_manager
    if _iot_registry_manager is None:
        iot_hub_host = os.environ.get("IotHubHostName")
        if iot_hub_host:
            credential = DefaultAzureCredential()
            _iot_registry_manager = IoTHubRegistryManager.from_token_credential(
                iot_hub_host, credential
            )
            logging.info("✅ IoT Hub Registry Manager initialized via Managed Identity")
        else:
            logging.warning("⚠️ IotHubHostName not configured. C2D feedback disabled.")
    return _iot_registry_manager
