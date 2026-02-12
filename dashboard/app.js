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
        chart: null,
        chartData: {
            labels: [],
            speed: [],
            rpm: []
        }
    },
    computed: {
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
        async fetchVehicles() {
            try {
                const response = await fetch(`${API_BASE}/vehicles`);
                const data = await response.json();
                this.vehicles = data;
                
                if (this.vehicles.length > 0) {
                    this.selectedVehicle = this.vehicles[0];
                    this.loadHistory(this.selectedVehicle);
                }
            } catch (error) {
                console.error("Errore caricamento veicoli:", error);
            }
        },

        async loadHistory(vehicleId) {
            // Reset stato
            this.logs = [];
            this.allData = [];
            this.clearChart();
            
            try {
                const response = await fetch(`${API_BASE}/history/${vehicleId}`);
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
            }
        },

        changeVehicle() {
            if (this.selectedVehicle) {
                this.loadHistory(this.selectedVehicle);
            }
        },

        async resetCurrent() {
            if (!this.selectedVehicle) return;
            if (!confirm(`Cancellare tutti i dati di ${this.selectedVehicle}?`)) return;

            try {
                const res = await fetch(`${API_BASE}/telemetry/${this.selectedVehicle}`, { method: 'DELETE' });
                const result = await res.json();
                console.log(`Deleted ${result.deleted} docs for ${this.selectedVehicle}`);
                
                this.allData = [];
                this.logs = [];
                this.latest = { speed: 0, rpm: 0, fuel_level: 100, ai_advice: 'Dati resettati.', alert_level: 'INFO' };
                this.clearChart();
            } catch (e) {
                console.error("Reset error:", e);
                alert("Errore durante il reset!");
            }
        },

        async resetAll() {
            if (!confirm('Cancellare TUTTI i dati di TUTTI i veicoli?')) return;

            try {
                const res = await fetch(`${API_BASE}/telemetry`, { method: 'DELETE' });
                const result = await res.json();
                console.log(`Deleted ${result.deleted} docs total`);

                this.allData = [];
                this.logs = [];
                this.latest = { speed: 0, rpm: 0, fuel_level: 100, ai_advice: 'Tutti i dati resettati.', alert_level: 'INFO' };
                this.clearChart();
            } catch (e) {
                console.error("Reset all error:", e);
                alert("Errore durante il reset!");
            }
        },

        async initSignalR() {
            try {
                this.statusMessage = 'Connessione in corso...';

                const connection = new signalR.HubConnectionBuilder()
                    .withUrl(API_BASE)
                    .configureLogging(signalR.LogLevel.Information)
                    .build();

                connection.on('newMessage', (message) => {
                    console.log("Dati ricevuti da SignalR:", message);
                    this.updateDashboard(message);
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

            } catch (err) {
                console.error("Errore SignalR:", err);
                this.statusMessage = 'Errore Connessione';
                setTimeout(() => this.initSignalR(), 5000);
            }
        },

        updateDashboard(data) {
            if (this.selectedVehicle && data.vehicle_id !== this.selectedVehicle) {
                return;
            }

            this.latest = data;
            this.allData.push(data);
            this.logs.unshift(data);
            if (this.logs.length > 50) this.logs.pop();
            this.addToChart(data);
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
        }
    },
    mounted() {
        this.initChart();
        this.fetchVehicles();
        this.initSignalR();
    }
});
