const app = new Vue({
    el: '#app',
    data: {
        isConnected: false,
        statusMessage: 'Disconnesso',
        latest: {
            speed: 0,
            rpm: 0,
            ai_advice: 'In attesa...'
        },
        logs: [],
        chart: null,
        chartData: {
            labels: [],
            speed: [],
            rpm: []
        }
    },
    methods: {
        async initSignalR() {
            try {
                this.statusMessage = 'Connessione in corso...';
                
                // 1. Chiamata a /api/negotiate per ottenere URL e Token
                // Logica intelligente: Se siamo in locale usa localhost, altrimenti usa Azure
                let API_BASE_URL = 'http://localhost:7071/api'; 
                
                if (window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost') {
                    // ☁️ SIAMO SU AZURE!
                    API_BASE_URL = 'https://func-ecofleet.azurewebsites.net/api';
                }

                console.log("Using API endpoint:", API_BASE_URL);
                
                const connection = new signalR.HubConnectionBuilder()
                    .withUrl(API_BASE_URL) 
                    .configureLogging(signalR.LogLevel.Information)
                    .build();

                // 2. Gestione eventi in arrivo
                connection.on('newMessage', (message) => {
                    console.log("Dati ricevuti da SignalR:", message);
                    this.updateDashboard(message);
                });

                connection.onclose(() => {
                    this.isConnected = false;
                    this.statusMessage = 'Disconnesso (Riprovo...)';
                    setTimeout(() => this.initSignalR(), 5000);
                });

                // 3. Avvio connessione
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
            // Aggiorna valori KPI
            this.latest = data;

            // Aggiungi a logs
            this.logs.unshift(data);
            if (this.logs.length > 50) this.logs.pop();

            // Aggiorna Grafico
            const timeLabel = new Date(data.timestamp).toLocaleTimeString();
            
            this.chart.data.labels.push(timeLabel);
            this.chart.data.datasets[0].data.push(data.speed);
            this.chart.data.datasets[1].data.push(data.rpm);

            // Mantieni solo gli ultimi 20 punti
            if (this.chart.data.labels.length > 20) {
                this.chart.data.labels.shift();
                this.chart.data.datasets[0].data.shift();
                this.chart.data.datasets[1].data.shift();
            }

            this.chart.update();
        },

        formatTime(isoString) {
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
                        backgroundColor: 'rgba(77, 163, 255, 0.1)',
                        data: [],
                        yAxisID: 'y'
                    }, {
                        label: 'RPM',
                        borderColor: '#ff4d4d',
                        backgroundColor: 'rgba(255, 77, 77, 0.1)',
                        data: [],
                        yAxisID: 'y1'
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
                            title: { display: true, text: 'Speed' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            title: { display: true, text: 'RPM' }
                        },
                        x: {
                            grid: { color: '#444' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: 'white' } }
                    }
                }
            });
        }
    },
    mounted() {
        this.initChart();
        this.initSignalR();
    }
});
