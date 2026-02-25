# API — Azure Functions Backend

Backend serverless costruito con **Azure Functions v4 (Python)**, organizzato in **Blueprint** modulari.

## Architettura

```
function_app.py          # Entry point — registra tutti i blueprint
├── blueprints/
│   ├── telemetry.py     # ProcessTelemetry: IoT Hub D2C → Cosmos DB + SignalR + advice-queue
│   ├── advice.py        # GenerateAdvice: advice-queue → Gemini AI → Cosmos + SignalR + C2D
│   ├── vehicles.py      # GET /api/vehicles — lista veicoli da Cosmos
│   ├── signalr.py       # Negoziazione SignalR per la dashboard
│   └── admin.py         # DELETE /api/telemetry — reset dati
└── shared/
    ├── ai_advisor.py    # Client Gemini 2.5 Flash Lite via LangChain (+ fallback rule-based)
    ├── cosmos_client.py # Singleton Cosmos DB client
    └── iot_hub.py       # IoT Hub Registry Manager (per invio C2D)
```

## Flusso Dati

1. **ProcessTelemetry** — triggerato da IoT Hub Event Hub. Salva telemetria su Cosmos DB, invia dati real-time alla dashboard via SignalR, e accoda la richiesta AI su `advice-queue`.
2. **GenerateAdvice** — triggerato dalla coda. Chiama Gemini per generare un consiglio, aggiorna il documento Cosmos, invia l'advice alla dashboard via SignalR, e manda un feedback C2D al veicolo.

## Servizi Azure Utilizzati

| Servizio | Scopo |
|----------|-------|
| IoT Hub (Event Hub endpoint) | Ricezione telemetria D2C |
| Cosmos DB | Persistenza telemetria + advice |
| SignalR Service | Push real-time alla dashboard |
| Storage Queue | Disaccoppiamento telemetria/AI |
| IoT Hub (C2D) | Feedback al veicolo |

## Configurazione

Le variabili d'ambiente sono definite in `local.settings.json` (locale) e nelle Application Settings (Azure):

- `CosmosDBConnectionString`
- `IoTHubEventHubConnectionString`, `IoTHubEventHubName`
- `SignalRConnectionString`
- `AzureStorageQueueConnectionString`
- `GOOGLE_API_KEY` (Gemini)
- `IOTHUB_SERVICE_CONNECTION_STRING` (C2D)

## Sviluppo Locale

```bash
cd api
pip install -r requirements.txt
func start
```
