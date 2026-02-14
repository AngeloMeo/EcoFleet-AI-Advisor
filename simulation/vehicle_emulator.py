import asyncio
import json
import random
import time
import os
import logging

from dotenv import load_dotenv
load_dotenv()

# Azure SDKs
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.hub import IoTHubRegistryManager
from azure.storage.queue import QueueClient, TextBase64EncodePolicy

# --- CONFIGURAZIONE LOGGER ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EcoFleetSimulator")

# Silenzia lo spam HTTP degli SDK Azure
for noisy in ["azure.core", "azure.iot", "azure.storage", "urllib3", "uamqp", "msrest"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

# --- CONFIGURAZIONE ENV ---
IOTHUB_SERVICE_CONN_STR = os.getenv("IOTHUB_SERVICE_CONNECTION_STRING")
STORAGE_CONN_STR = os.getenv("STORAGE_CONNECTION_STRING")
QUEUE_NAME = "telemetry-queue"

VEHICLE_PREFIX = "Bus-"
VEHICLE_COUNT = 5
TELEMETRY_INTERVAL_SEC = 5  # Secondi tra un invio e l'altro per ogni veicolo

class VehicleSimulator:
    def __init__(self, vehicle_id, device_conn_str, queue_client, aggressive=False):
        self.vehicle_id = vehicle_id
        self.device_conn_str = device_conn_str
        self.queue_client = queue_client
        self.device_client = None
        self.running = True
        self.last_feedback = "In attesa di feedback..."
        self.aggressive = aggressive
        
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
            
            # Callback moderna per feedback C2D (sostituisce receive_message deprecato)
            def on_message(message):
                feedback = message.data.decode('utf-8')
                self.last_feedback = feedback
                logger.warning(f"🔔 [{self.vehicle_id}] 📩 FEEDBACK: {feedback}")
                if "slow" in feedback.lower() or "rallenta" in feedback.lower():
                    logger.info(f"[{self.vehicle_id}] 🛑 Braking due to feedback!")
                    self.speed *= 0.8
            
            self.device_client.on_message_received = on_message
            await self.device_client.connect()
            logger.info(f"[{self.vehicle_id}] ✅ Connected to IoT Hub")
        except Exception as e:
            logger.error(f"[{self.vehicle_id}] ❌ Connection Failed: {e}")

    async def update_physics(self):
        if self.aggressive:
            # 🔥 GUIDA AGGRESSIVA: accelera sempre, non scala mai, frena poco
            self.speed += random.uniform(5, 25)
            if random.random() < 0.05:  # 5% chance frenata
                self.speed -= random.uniform(10, 30)
            self.speed -= 0.1
            if self.speed < 20: self.speed = 20  # Mai troppo lento
            if self.speed > 180: self.speed = 180
            # Resta in marce basse → RPM altissimi
            if self.gear > 3: self.gear = 3
        else:
            # Decisione di guida: accelera, frena, o guida aggressivamente
            action = random.random()
            
            if action < 0.10:
                # 10% chance: frenata brusca (traffico, semaforo)
                brake_force = random.uniform(5, 15)
                self.speed -= brake_force
            elif action < 0.20:
                # 10% chance: accelerata aggressiva
                self.speed += random.uniform(8, 20)
            elif self.speed < self.gears[self.gear]['max'] - 5:
                # Accelerazione normale
                self.speed += random.uniform(1.0, 5.0)
            elif self.speed > self.gears[self.gear]['max']:
                self.speed -= random.uniform(1.0, 3.0)
            
            # Attrito/resistenza
            self.speed -= 0.2
            if self.speed < 0: self.speed = 0
            if self.speed > 180: self.speed = 180  # Cap fisico
            
        # RPM con variazione marcata
        base_rpm = self.speed * self.gears[self.gear]['ratio'] * 40
        self.rpm = base_rpm + 800 + random.uniform(-100, 100)
        if self.rpm < 600: self.rpm = 600
        if self.rpm > 6000: self.rpm = 6000
        
        # Cambio marcia
        if self.rpm > 3500 and self.gear < 6:
            self.gear += 1
            self.rpm -= 1500
        elif self.rpm < 1200 and self.gear > 1 and self.speed > 10:
            self.gear -= 1
            self.rpm += 1000

        # Consumo proporzionale a RPM (esagerato: ~3 min per svuotare il serbatoio)
        fuel_burn = (self.rpm / 2500.0) * 2.0
        self.fuel_level -= fuel_burn
        if self.fuel_level <= 0:
            self.fuel_level = 0  # Segnala vuoto, il refuel avviene nel loop run()

    def get_telemetry(self):
        return {
            "vehicle_id": self.vehicle_id,
            "speed": round(self.speed, 2),
            "rpm": int(self.rpm),
            "gear": self.gear,
            "fuel_level": round(self.fuel_level, 2),
            "timestamp": time.time()
        }

    async def run(self):
        while self.running:
            await self.update_physics()
            data = self.get_telemetry()
            
            logger.info(
                f"📤 [{self.vehicle_id}] "
                f"⚙️ G{data['gear']} | "
                f"🚀 {data['speed']:6.1f} km/h | "
                f"🔄 {data['rpm']:4d} rpm | "
                f"⛽ {data['fuel_level']:5.1f}% | "
                f"🤖 {self.last_feedback}"
            )
            
            try:
                self.queue_client.send_message(json.dumps(data))
            except Exception as e:
                logger.error(f"[{self.vehicle_id}] Queue send error: {e}")

            # Refuel realistico: fermata ai box
            if self.fuel_level <= 0:
                logger.warning(f"⛽🔴 [{self.vehicle_id}] SERBATOIO VUOTO! Pit-stop rifornimento...")
                self.speed = 0
                self.rpm = 800
                self.gear = 1
                await asyncio.sleep(2)  # Pausa pit-stop
                self.fuel_level = 100.0
                logger.warning(f"⛽🟢 [{self.vehicle_id}] Rifornimento completato! Si riparte.")
                
            await asyncio.sleep(TELEMETRY_INTERVAL_SEC + random.uniform(0, 1))

    async def stop(self):
        self.running = False
        if self.device_client:
            await self.device_client.disconnect()
            logger.info(f"[{self.vehicle_id}] Disconnected.")

def provision_fleet(service_conn_string, count):
    """Crea device SOLO se non esistono già. Usa create_device_with_sas per la creazione."""
    import base64
    import uuid

    registry_manager = IoTHubRegistryManager(service_conn_string)
    devices_config = []
    
    logger.info(f"🔧 Checking Fleet Status ({count} vehicles needed)...")
    
    for i in range(1, count + 1):
        device_id = f"{VEHICLE_PREFIX}{i:02d}"
        created_new = False
        
        try:
            device = registry_manager.get_device(device_id)
        except Exception:
            # Device non esiste, crealo con chiavi SAS auto-generate
            primary_key = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode()
            secondary_key = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode()
            device = registry_manager.create_device_with_sas(
                device_id, primary_key, secondary_key, "enabled"
            )
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
        fleet_config = provision_fleet(IOTHUB_SERVICE_CONN_STR, VEHICLE_COUNT)
    except Exception as e:
        logger.critical(f"Provisioning Failed: {e}")
        return

    # 3. Avvio Simulazione
    simulators = []
    tasks = []

    logger.info("🚀 Starting Fleet Simulation... (CTRL+C to stop)")
    
    for conf in fleet_config:
        is_aggressive = conf['id'] == "Bus-05"
        sim = VehicleSimulator(conf['id'], conf['conn_str'], queue_client, aggressive=is_aggressive)
        if is_aggressive:
            logger.warning(f"🔥 {conf['id']} è in modalità PAZZO SCATENATO!")

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
