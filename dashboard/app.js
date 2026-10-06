// ── Application Insights ──
const appInsights = new Microsoft.ApplicationInsights.ApplicationInsights({
    config: {
        connectionString: 'InstrumentationKey=47839450-6abb-4d58-ab4d-609959825ba0;IngestionEndpoint=https://italynorth-0.in.applicationinsights.azure.com/;LiveEndpoint=https://italynorth.livediagnostics.monitor.azure.com/;ApplicationId=963dc218-6fe0-47c2-965a-dcd3a48c812f',
        disableFetchTracking: false,
        enableCorsCorrelation: true,
        enableRequestHeaderTracking: true,
        enableResponseHeaderTracking: true
    }
});
appInsights.loadAppInsights();
appInsights.trackPageView({ name: 'EcoFleet Dashboard' });

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:7071/api'
    : 'https://func-ecofleet-euhtfkfyhpbsapfp.italynorth-01.azurewebsites.net/api';

const app = new Vue({
    el: '#app',
    data: {
        isConnected: false,
        statusMessage: 'Disconnesso',
        latest: {
            speed: 0,
            rpm: 0,
            fuel_level: 100,
            ai_advice: 'In attesa...',
            alert_level: 'INFO'
        },
        vehicles: [],
        selectedVehicle: '',
        logs: [],
        allData: [],   // Tutti i data point del veicolo selezionato (per stats)
        user: null,
        authToken: '',
        showProfileMenu: false,
        showInstallBtn: false,
        deferredPrompt: null,
        chart: null,
        chartData: {
            labels: [],
            speed: [],
            rpm: []
        }
    },
    computed: {
        userInitials() {
            if (!this.user || !this.user.name) return '?';
            return this.user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        },
        avgSpeed() {
            if (this.allData.length === 0) return '—';
            const sum = this.allData.reduce((a, d) => a + (d.speed || 0), 0);
            return (sum / this.allData.length).toFixed(1);
        },
        avgRpm() {
            if (this.allData.length === 0) return '—';
            const sum = this.allData.reduce((a, d) => a + (d.rpm || 0), 0);
            return Math.round(sum / this.allData.length);
        },
        totalFuelConsumed() {
            if (this.allData.length < 2) return '0.0';
            let totalBurned = 0;
            for (let i = 1; i < this.allData.length; i++) {
                const prev = this.allData[i - 1].fuel_level ?? 100;
                const curr = this.allData[i].fuel_level ?? 100;
                const delta = prev - curr;
                // Conta solo il consumo reale (delta > 0). Ignora i refuel (delta < 0)
                if (delta > 0) totalBurned += delta;
            }
            return totalBurned.toFixed(1);
        },
        dataPointCount() {
            return this.allData.length;
        },
        fuelClass() {
            const lvl = this.latest.fuel_level || 0;
            if (lvl > 50) return 'fuel-high';
            if (lvl > 20) return 'fuel-mid';
            return 'fuel-low';
        }
    },
    methods: {
        handleAuthExpiration() {
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') return;
            console.warn('⚠️ Token scaduto o non valido! Reindirizzamento al login...');
            this.statusMessage = 'Sessione scaduta, riautenticazione in corso...';
            // Forza logout e poi re-login su Entra ID per pulire i cookie vecchi
            window.location.href = '/.auth/logout?post_logout_redirect_uri=/.auth/login/aad';
        },

        async fetchUserProfile() {
            try {
                const res = await fetch('/.auth/me');
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.length > 0) {
                        const claims = data[0].user_claims || [];
                        const getClaim = (type) => {
                            const c = claims.find(c => c.typ === type || c.typ.endsWith('/' + type));
                            return c ? c.val : '';
                        };
                        this.user = {
                            name: getClaim('name') || data[0].user_id || 'Utente',
                            email: getClaim('preferred_username') || getClaim('emailaddress') || data[0].user_id || ''
                        };
                        this.authToken = data[0].id_token || '';
                    }
                }
            } catch (e) {
                console.log('Auth info non disponibile (dev locale)');
                appInsights.trackException({ exception: e, properties: { operation: 'fetchUserProfile' } });
            }
        },

        async refreshAuthToken() {
            try {
                // Chiedi a EasyAuth di rinnovare il token
                const res = await fetch('/.auth/refresh');
                if (res.status === 401 || res.status === 403) {
                    this.handleAuthExpiration();
                    return;
                }
                // Ri-carica il token aggiornato
                await this.fetchUserProfile();
                console.log('🔄 Token rinnovato');
            } catch (e) {
                console.warn('⚠️ Impossibile rinnovare il token:', e);
                appInsights.trackException({ exception: e, properties: { operation: 'refreshAuthToken' } });
            }
        },

        startTokenRefreshTimer() {
            // Rinnova il token ogni 45 minuti (EasyAuth scade dopo ~1h)
            setInterval(() => this.refreshAuthToken(), 45 * 60 * 1000);
        },

        authHeaders() {
            if (!this.authToken) return {};
            return { 'Authorization': `Bearer ${this.authToken}` };
        },

        async fetchVehicles() {
            try {
                const response = await fetch(`${API_BASE}/vehicles`, { headers: this.authHeaders() });
                if (response.status === 401) {
                    this.handleAuthExpiration();
                    return;
                }
                const data = await response.json();
                this.vehicles = data;
                
                if (this.vehicles.length > 0) {
                    this.selectedVehicle = this.vehicles[0];
                    this.loadHistory(this.selectedVehicle);
                }
            } catch (error) {
                console.error("Errore caricamento veicoli:", error);
                appInsights.trackException({ exception: error, properties: { operation: 'fetchVehicles' } });
            }
        },

        async loadHistory(vehicleId) {
            // Reset stato
            this.logs = [];
            this.allData = [];
            this.clearChart();
            
            try {
                const response = await fetch(`${API_BASE}/history/${vehicleId}`, { headers: this.authHeaders() });
                const history = await response.json();
                
                // history arriva ordinato DESC, lo invertiamo per cronologia
                history.reverse().forEach(point => {
                    this.allData.push(point);
                    this.addToChart(point);
                    this.logs.unshift(point);
                });

                // Aggiorna KPI con l'ultimo punto
                if (history.length > 0) {
                    this.latest = history[history.length - 1];
                }

            } catch (error) {
                console.error("Errore caricamento storico:", error);
                appInsights.trackException({ exception: error, properties: { operation: 'loadHistory', vehicleId } });
            }
        },

        changeVehicle() {
            if (this.selectedVehicle) {
                appInsights.trackEvent({ name: 'VehicleChanged' }, { vehicleId: this.selectedVehicle });
                this.loadHistory(this.selectedVehicle);
            }
        },

        async resetCurrent() {
            if (!this.selectedVehicle) return;
            if (!confirm(`Cancellare tutti i dati di ${this.selectedVehicle}?`)) return;

            try {
                const res = await fetch(`${API_BASE}/telemetry/${this.selectedVehicle}`, { method: 'DELETE', headers: this.authHeaders() });
                if (!res.ok) {
                    const errText = await res.text();
                    console.error(`Reset failed (${res.status}):`, errText);
                    alert(`Errore ${res.status}: ${errText}`);
                    return;
                }
                const result = await res.json();
                console.log(`Deleted ${result.deleted} docs for ${this.selectedVehicle}`);
                appInsights.trackEvent({ name: 'ResetVehicle' }, { vehicleId: this.selectedVehicle, deletedCount: result.deleted });
                
                this.allData = [];
                this.logs = [];
                this.latest = { speed: 0, rpm: 0, fuel_level: 100, ai_advice: 'Dati resettati.', alert_level: 'INFO' };
                this.clearChart();
            } catch (e) {
                console.error("Reset error:", e);
                appInsights.trackException({ exception: e, properties: { operation: 'resetCurrent', vehicleId: this.selectedVehicle } });
                alert("Errore durante il reset: " + e.message);
            }
        },

        async resetAll() {
            if (!confirm('Cancellare TUTTI i dati di TUTTI i veicoli?')) return;

            try {
                const res = await fetch(`${API_BASE}/telemetry`, { method: 'DELETE', headers: this.authHeaders() });
                if (!res.ok) {
                    const errText = await res.text();
                    console.error(`Reset all failed (${res.status}):`, errText);
                    alert(`Errore ${res.status}: ${errText}`);
                    return;
                }
                const result = await res.json();
                console.log(`Deleted ${result.deleted} docs total`);
                appInsights.trackEvent({ name: 'ResetAll' }, { deletedCount: result.deleted });

                this.allData = [];
                this.logs = [];
                this.latest = { speed: 0, rpm: 0, fuel_level: 100, ai_advice: 'Tutti i dati resettati.', alert_level: 'INFO' };
                this.clearChart();
            } catch (e) {
                console.error("Reset all error:", e);
                appInsights.trackException({ exception: e, properties: { operation: 'resetAll' } });
                alert("Errore durante il reset: " + e.message);
            }
        },

        async initSignalR() {
            try {
                this.statusMessage = 'Connessione in corso...';

                const signalROptions = this.authToken
                    ? { accessTokenFactory: () => this.authToken }
                    : {};

                const connection = new signalR.HubConnectionBuilder()
                    .withUrl(API_BASE, signalROptions)
                    .configureLogging(signalR.LogLevel.Information)
                    .build();

                connection.on('newTelemetry', (message) => {
                    console.log("📡 Telemetry ricevuta:", message);
                    this.updateDashboard(message);
                });

                connection.on('newAdvice', (advice) => {
                    console.log("🤖 AI Advice ricevuto:", advice);
                    this.updateAdvice(advice);
                });

                connection.onclose(() => {
                    this.isConnected = false;
                    this.statusMessage = 'Disconnesso (Riprovo...)';
                    setTimeout(() => this.initSignalR(), 5000);
                });

                await connection.start();
                this.isConnected = true;
                this.statusMessage = 'Connesso a SignalR 🟢';
                console.log("SignalR Connected!");
                appInsights.trackEvent({ name: 'SignalRConnected' });

            } catch (err) {
                console.error("Errore SignalR:", err);
                if (err.message && err.message.includes('401')) {
                    this.handleAuthExpiration();
                    return;
                }
                appInsights.trackException({ exception: err, properties: { operation: 'initSignalR' } });
                this.statusMessage = 'Errore Connessione';
                setTimeout(() => this.initSignalR(), 5000);
            }
        },

        updateDashboard(data) {
            if (this.selectedVehicle && data.vehicle_id !== this.selectedVehicle) {
                return;
            }
            appInsights.trackEvent({ name: 'TelemetryReceived' }, { vehicleId: data.vehicle_id, speed: data.speed, rpm: data.rpm });

            // Preserva l'advice esistente se la nuova telemetria non ne ha uno
            if (!data.ai_advice && this.latest && this.latest.vehicle_id === data.vehicle_id) {
                data.ai_advice = this.latest.ai_advice;
                data.alert_level = this.latest.alert_level;
            }
            this.latest = data;
            this.allData.push(data);
            this.logs.unshift(data);
            if (this.logs.length > 50) this.logs.pop();
            this.addToChart(data);
        },

        updateAdvice(advice) {
            // Aggiorna l'advice nella card KPI se è il veicolo corrente
            if (this.latest && this.latest.vehicle_id === advice.vehicle_id) {
                this.latest.ai_advice = advice.ai_advice;
                this.latest.alert_level = advice.alert_level;
            }
            // Aggiorna anche il log corrispondente
            const logEntry = this.logs.find(
                l => l.vehicle_id === advice.vehicle_id && !l.ai_advice
            );
            if (logEntry) {
                logEntry.ai_advice = advice.ai_advice;
                logEntry.alert_level = advice.alert_level;
            }
        },

        addToChart(data) {
            const ts = data.timestamp;
            // timestamp può essere ISO string o epoch
            const timeLabel = typeof ts === 'number'
                ? new Date(ts * 1000).toLocaleTimeString()
                : new Date(ts).toLocaleTimeString();

            this.chart.data.labels.push(timeLabel);
            this.chart.data.datasets[0].data.push(data.speed);
            this.chart.data.datasets[1].data.push(data.rpm);

            if (this.chart.data.labels.length > 30) {
                this.chart.data.labels.shift();
                this.chart.data.datasets[0].data.shift();
                this.chart.data.datasets[1].data.shift();
            }

            this.chart.update('none'); // 'none' = skip animations for performance
        },

        clearChart() {
            if (!this.chart) return;
            this.chart.data.labels = [];
            this.chart.data.datasets[0].data = [];
            this.chart.data.datasets[1].data = [];
            this.chart.update();
        },

        formatTime(isoString) {
            if (typeof isoString === 'number') return new Date(isoString * 1000).toLocaleTimeString();
            return new Date(isoString).toLocaleTimeString();
        },

        initChart() {
            const ctx = document.getElementById('telemetryChart').getContext('2d');
            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Velocità (km/h)',
                        borderColor: '#4da3ff',
                        backgroundColor: 'rgba(77, 163, 255, 0.08)',
                        data: [],
                        yAxisID: 'y',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true
                    }, {
                        label: 'RPM',
                        borderColor: '#a855f7',
                        backgroundColor: 'rgba(168, 85, 247, 0.08)',
                        data: [],
                        yAxisID: 'y1',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Speed (km/h)', color: '#888' },
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#888' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            title: { display: true, text: 'RPM', color: '#888' },
                            ticks: { color: '#888' }
                        },
                        x: {
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#888', maxRotation: 0 }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: '#ccc', usePointStyle: true, padding: 16 }
                        }
                    }
                }
            });
        },

        installPwa() {
            if (!this.deferredPrompt) return;
            this.deferredPrompt.prompt();
            this.deferredPrompt.userChoice.then((choice) => {
                console.log('[PWA] Scelta utente:', choice.outcome);
                this.deferredPrompt = null;
                this.showInstallBtn = false;
            });
        }
    },
    async mounted() {
        this.initChart();
        await this.fetchUserProfile(); // prima carica il token
        this.startTokenRefreshTimer(); // rinnova automaticamente ogni 45min
        this.fetchVehicles();
        this.initSignalR();

        // Chiudi dropdown profilo cliccando fuori
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.profile-wrapper')) {
                this.showProfileMenu = false;
            }
        });

        // ── PWA Install Prompt ──
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallBtn = true;
            console.log('[PWA] Install prompt disponibile');
        });

        window.addEventListener('appinstalled', () => {
            this.showInstallBtn = false;
            this.deferredPrompt = null;
            console.log('[PWA] App installata!');
        });
    }
});
