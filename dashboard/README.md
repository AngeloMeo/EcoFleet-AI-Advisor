# Dashboard — Live Monitoring Frontend

Dashboard real-time costruita con **Vue 2**, **Chart.js** e **SignalR** per il monitoraggio della flotta EcoFleet.

## Tecnologie

| Libreria | Versione | Scopo |
|----------|----------|-------|
| Vue.js | 2.x | Framework UI reattivo |
| Chart.js | latest | Grafici velocità/RPM in tempo reale |
| SignalR | 6.0.1 | Ricezione push real-time dal backend |
| Application Insights | SDK 3.x | Telemetria client-side (page views, errori, custom events) |

## Funzionalità

- **KPI Cards** — Velocità, RPM, carburante e consiglio AI aggiornati in real-time
- **Statistiche aggregate** — Media velocità, media RPM, carburante consumato, letture totali
- **Grafico live** — Andamento velocità e RPM con finestra scorrevole a 30 punti
- **Selettore veicolo** — Carica lo storico dal backend (Cosmos DB) per ogni veicolo
- **Reset dati** — Cancella telemetria per singolo veicolo o per tutta la flotta
- **Autenticazione** — Integrazione con Azure EasyAuth (profilo utente + token refresh)
- **Application Insights** — Traccia page views, chiamate API, errori JS e custom events

### Custom Events Tracciati

| Evento | Trigger |
|--------|---------|
| `VehicleChanged` | Cambio veicolo selezionato |
| `TelemetryReceived` | Ricezione dato real-time via SignalR |
| `ResetVehicle` | Reset dati singolo veicolo |
| `ResetAll` | Reset globale |
| `SignalRConnected` | Connessione SignalR stabilita |

## Struttura

```
dashboard/
├── index.html    # Pagina HTML con template Vue
├── app.js        # Logica Vue (dati, metodi, SignalR, App Insights)
├── style.css     # Stili dark theme
└── package.json  # Metadata npm
```

## Sviluppo Locale

La dashboard è un'app statica. Per lavorare localmente servire i file con un server HTTP qualsiasi:

```bash
cd dashboard
npx serve .
```

In locale, le API puntano a `http://localhost:7071/api` (Azure Functions in locale). In produzione, puntano all'endpoint Azure automaticamente.
