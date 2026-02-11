import asyncio
import json
import random
import time
import os
import sys
import logging

# Azure SDKs
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.hub import IoTHubRegistryManager
from azure.storage.queue import QueueClient, TextBase64EncodePolicy

# --- CONFIGURAZIONE LOGGER ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EcoFleetSimulator")

# --- CONFIGURAZIONE ENV ---
IOTHUB_SERVICE_CONN_STR = os.getenv("IOTHUB_SERVICE_CONNECTION_STRING")
STORAGE_CONN_STR = os.getenv("STORAGE_CONNECTION_STRING")
QUEUE_NAME = "telemetry-queue"

VEHICLE_PREFIX = "Bus-"
VEHICLE_COUNT = 5

class VehicleSimulator:
    def __init__(self, vehicle_id, device_conn_str, queue_client):
        self.vehicle_id = vehicle_id
        self.device_conn_str = device_conn_str
        self.queue_client = queue_client
        self.device_client = None
        self.running = True
        
        # Fisica Base
        self.speed = 0.0
        self.rpm = 800.0
        self.gear = 1
        self.fuel_level = 100.0
        
        self.gears = {
            1: {'ratio': 4.0, 'min': 0, 'max': 30},
            2: {'ratio': 2.5, 'min': 20, 'max': 50},
            3: {'ratio': 1.8, 'min': 40, 'max': 80},
            4: {'ratio': 1.2, 'min': 60, 'max': 110},
            5: {'ratio': 0.9, 'min': 80, 'max': 140},
            6: {'ratio': 0.7, 'min': 100, 'max': 180}
        }

    async def connect(self):
        try:
            self.device_client = IoTHubDeviceClient.create_from_connection_string(self.device_conn_str)
            await self.device_client.connect()
            logger.info(f"[{self.vehicle_id}] ✅ Connected to IoT Hub")
            asyncio.create_task(self.listen_for_feedback())
        except Exception as e:
            logger.error(f"[{self.vehicle_id}] ❌ Connection Failed: {e}")

    async def update_physics(self):
        # ... (Logica fisica invaiata) ...
        if self.speed < self.gears[self.gear]['max'] - 5:
            self.speed += random.uniform(0.5, 2.0)
        elif self.speed > self.gears[self.gear]['max']:
            self.speed -= 1.0
        
        self.speed -= 0.1
        if self.speed < 0: self.speed = 0
            
        base_rpm = self.speed * self.gears[self.gear]['ratio'] * 40
        self.rpm = base_rpm + 800 + random.uniform(-20, 20)
        
        if self.rpm > 3500 and self.gear < 6:
            self.gear += 1
            self.rpm -= 1500
        elif self.rpm < 1200 and self.gear > 1 and self.speed > 10:
            self.gear -= 1
            self.rpm += 1000

        self.fuel_level -= (self.rpm / 10000.0) * 0.05
        if self.fuel_level < 0: self.fuel_level = 100

    def get_telemetry(self):
        return {
            "vehicle_id": self.vehicle_id,
            "speed": round(self.speed, 2),
            "rpm": int(self.rpm),
            "gear": self.gear,
            "fuel_level": round(self.fuel_level, 2),
            "timestamp": time.time()
        }

    async def listen_for_feedback(self):
        while self.running:
            try:
                # Listener bloccante (attende msg)
                msg = await self.device_client.receive_message()
                feedback = msg.data.decode('utf-8')
                logger.warning(f"🔔 [{self.vehicle_id}] 📩 FEEDBACK RECEIVED: {feedback}")
                
                # Reazione simulata: se dicono rallenta, freniamo!
                if "slow" in feedback.lower() or "rallenta" in feedback.lower():
                    logger.info(f"[{self.vehicle_id}] ⚠️ Braking due to feedback!")
                    self.speed *= 0.8 

            except Exception as e:
                # logger.error(f"[{self.vehicle_id}] Listener Error: {e}")
                pass

    async def run(self):
        while self.running:
            await self.update_physics()
            data = self.get_telemetry()
            
            # Invio Telemetria
            try:
                self.queue_client.send_message(json.dumps(data))
                # logger.debug(f"[{self.vehicle_id}] Sent Telemetry: {self.speed} km/h") 
            except Exception:
                pass # Queue error logic suppressed for cleaner output
                
            await asyncio.sleep(2 + random.uniform(0, 1))

    async def stop(self):
        self.running = False
        if self.device_client:
            await self.device_client.disconnect()
            logger.info(f"[{self.vehicle_id}] Disconnected.")

def provision_fleet(service_conn_string, count):
    """Crea device SOLO se non esistono già"""
    registry_manager = IoTHubRegistryManager(service_conn_string)
    devices_config = []
    
    logger.info(f"🔧 Checking Fleet Status ({count} vehicles needed)...")
    
    for i in range(1, count + 1):
        device_id = f"{VEHICLE_PREFIX}{i:02d}"
        created_new = False
        
        try:
            device = registry_manager.get_device(device_id)
        except Exception:
            # Device non esiste, crealo
            device = registry_manager.create_device(device_id)
            created_new = True
            
        # Get Key
        primary_key = device.authentication.symmetric_key.primary_key
        hub_name = service_conn_string.split(";")[0].split("=")[1]
        conn_str = f"HostName={hub_name};DeviceId={device_id};SharedAccessKey={primary_key}"
        
        status_icon = "✨ Created" if created_new else "♻️ Reused"
        logger.info(f"   [{status_icon}] {device_id}")
        
        devices_config.append({"id": device_id, "conn_str": conn_str})
        
    return devices_config

async def main():
    if not IOTHUB_SERVICE_CONN_STR or not STORAGE_CONN_STR:
        logger.error("Missing Environment Variables! Set IOTHUB_SERVICE_CONNECTION_STRING & STORAGE_CONNECTION_STRING")
        return

    # 1. Setup Queue
    try:
        queue_client = QueueClient.from_connection_string(
            STORAGE_CONN_STR, 
            QUEUE_NAME,
            message_encode_policy=TextBase64EncodePolicy()
        )
        logger.info(f"✅ Connected to Storage Queue: {QUEUE_NAME}")
    except Exception as e:
        logger.critical(f"Queue Connection Failed: {e}")
        return

    # 2. Provisioning (Persistente)
    try:
        fleet_config = (IOTHUB_SERVICE_CONN_STR, VEHICLE_COUNT)
    except Exception as e:
        logger.critical(f"Provisioning Failed: {e}")
        return

    # 3. Avvio Simulazione
    simulators = []
    tasks = []

    logger.info("🚀 Starting Fleet Simulation... (CTRL+C to stop)")
    
    for conf in fleet_config:
        sim = VehicleSimulator(conf['id'], conf['conn_str'], queue_client)
        simulators.append(sim)
        await sim.connect()
        tasks.append(asyncio.create_task(sim.run()))
        
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("🛑 Stopping Simulation...")
        for sim in simulators:
            await sim.stop()
        # NESSUN CLEANUP DI DEVICE! Li lasciamo lì per la prossima volta.

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 
