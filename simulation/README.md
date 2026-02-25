# Simulation — Vehicle Fleet Emulator

Simulatore di flotta che genera telemetria realistica e la invia ad **Azure IoT Hub** via protocollo D2C (Device-to-Cloud).

## Componenti

| File | Descrizione |
|------|-------------|
| `vehicle_emulator.py` | Emulatore principale — simula N veicoli in parallelo |
| `test_manual.py` | Test manuale per invio singolo messaggio |
| `test_c2d.py` | Test ricezione messaggi Cloud-to-Device |

## Come Funziona

`vehicle_emulator.py` crea una flotta di **5 veicoli** (`Bus-0` ... `Bus-4`) che:

1. **Provisioning** — Registra automaticamente i device su IoT Hub se non esistono
2. **Connessione** — Ogni veicolo si connette ad IoT Hub con la propria connection string
3. **Simulazione fisica** — Aggiorna velocità, RPM, marcia e carburante con un modello fisico realistico (accelerazione, frenata, cambio marcia)
4. **Invio telemetria** — Ogni `TELEMETRY_INTERVAL_SEC` secondi invia un messaggio D2C con: `speed`, `rpm`, `fuel_level`, `gear`, `vehicle_id`, `timestamp`
5. **Ricezione C2D** — Ascolta messaggi di feedback dall'AI Advisor e li stampa in console

### Modalità di Guida

- **Normale** — Guida tranquilla con accelerazioni graduali
- **Aggressiva** — RPM alti, velocità elevate, consumo maggiorato (+50%)

## Configurazione

Crea un file `.env` nella cartella `simulation/`:

```env
IOTHUB_SERVICE_CONNECTION_STRING=HostName=...;SharedAccessKeyName=...;SharedAccessKey=...
```

## Esecuzione

```bash
cd simulation
pip install -r requirements.txt
python vehicle_emulator.py
```

La simulazione gira finché non viene interrotta con `Ctrl+C`. Ogni veicolo è un task asyncio indipendente.
