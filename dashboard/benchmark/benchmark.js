// ══════════════════════════════════════════════════════════════
// EcoFleet PWA — Synthetic Benchmark Suite
// Metodologia: Biørn-Hansen et al. (2020)
// KPI: Time-to-Completion (ms), PreRAM (MB), ComputedRAM (MB)
// ══════════════════════════════════════════════════════════════

// ── Error Logging per Mobile ──
window.onerror = function(msg, url, line, col, error) {
    console.error(`[Global Error] ${msg} at ${line}:${col}`, error);
    updateStatus(`❌ Errore critico: ${msg}`);
};
window.addEventListener("unhandledrejection", function(promiseRejectionEvent) { 
    console.error('[Unhandled Rejection]', promiseRejectionEvent.reason);
});

// ── Application Insights (stessa istanza della dashboard) ──
try {
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
    appInsights.trackPageView({ name: 'Benchmark Suite' });
    window.appInsights = appInsights;
} catch (e) {
    console.error("AppInsights init failed (forse adblocker?):", e);
}

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:7071/api'
    : 'https://func-ecofleet-euhtfkfyhpbsapfp.italynorth-01.azurewebsites.net/api';

// ── Configurazione ──
const CONFIG = {
    iterations: 10,          // Ripetizioni per test (robustezza statistica)
    jsonRecords: 10000,      // Record per JSON benchmark
    cacheEntries: 500,       // Blob da scrivere/leggere in Cache API
    idbRecords: 5000,        // Record per IndexedDB
    domElements: 1000,       // Elementi per DOM Stress
    fetchRepetitions: 10,    // Chiamate REST ripetute
    geoTimeout: 10000,       // Timeout geolocalizzazione (ms)
    accelSamples: 100        // Campioni accelerometro
};

// ── Utility: Memoria ──
function getMemoryMB() {
    if (performance.memory) {
        return performance.memory.usedJSHeapSize / (1024 * 1024);
    }
    return null; // Non supportato (Firefox, Safari)
}

function formatMem(val) {
    return val !== null ? val.toFixed(2) : 'N/A';
}

// ── Utility: Statistiche ──
function computeStats(values) {
    const n = values.length;
    const mean = values.reduce((a, b) => a + b, 0) / n;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n;
    const stdDev = Math.sqrt(variance);
    return { mean: +mean.toFixed(2), min: +min.toFixed(2), max: +max.toFixed(2), stdDev: +stdDev.toFixed(2) };
}

// ── Utility: Delay ──
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ══════════════════════════════════════════════════════════════
// TEST 1: JSON Processing (CPU-bound Microbenchmark)
// Equivalente: data processing / serializzazione del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkJSON() {
    const times = [];

    // Genera payload simulando telemetria veicolare
    const payload = Array.from({ length: CONFIG.jsonRecords }, (_, i) => ({
        vehicle_id: `VEH-${String(i).padStart(4, '0')}`,
        timestamp: Date.now(),
        speed: Math.random() * 200,
        rpm: Math.random() * 8000,
        fuel_level: Math.random() * 100,
        latitude: 40.77 + Math.random(),
        longitude: 14.79 + Math.random(),
        ai_advice: 'Mantenere velocità costante per efficienza ottimale',
        alert_level: ['INFO', 'WARNING', 'CRITICAL'][Math.floor(Math.random() * 3)]
    }));

    const preRAM = getMemoryMB();

    for (let i = 0; i < CONFIG.iterations; i++) {
        const t0 = performance.now();
        const stringified = JSON.stringify(payload);
        JSON.parse(stringified);
        const t1 = performance.now();
        times.push(t1 - t0);
    }

    const postRAM = getMemoryMB();
    const stats = computeStats(times);

    return {
        test: 'JSON Processing',
        category: 'Microbenchmark (CPU)',
        detail: `${CONFIG.jsonRecords} record × ${CONFIG.iterations} iterazioni`,
        ttc: stats,
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 2: Cache API I/O (Synthetic — equivalente File System)
// Equivalente: File I/O read/write del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkCacheAPI() {
    const writeTimes = [];
    const readTimes = [];
    const cacheName = 'benchmark-cache';

    const preRAM = getMemoryMB();

    for (let iter = 0; iter < CONFIG.iterations; iter++) {
        // ── WRITE ──
        const cache = await caches.open(cacheName);
        const t0w = performance.now();
        const writePromises = [];
        for (let i = 0; i < CONFIG.cacheEntries; i++) {
            const data = JSON.stringify({ id: i, data: 'x'.repeat(200), timestamp: Date.now() });
            const response = new Response(data, { headers: { 'Content-Type': 'application/json' } });
            writePromises.push(cache.put(`/bench/item-${i}`, response));
        }
        await Promise.all(writePromises);
        const t1w = performance.now();
        writeTimes.push(t1w - t0w);

        // ── READ ──
        const t0r = performance.now();
        const readPromises = [];
        for (let i = 0; i < CONFIG.cacheEntries; i++) {
            readPromises.push(cache.match(`/bench/item-${i}`).then(r => r?.text()));
        }
        await Promise.all(readPromises);
        const t1r = performance.now();
        readTimes.push(t1r - t0r);

        // Pulisci
        await caches.delete(cacheName);
    }

    const postRAM = getMemoryMB();

    return {
        test: 'Cache API I/O',
        category: 'Synthetic (File System)',
        detail: `${CONFIG.cacheEntries} entry × ${CONFIG.iterations} iter — Write + Read`,
        ttc: computeStats(writeTimes.map((w, i) => w + readTimes[i])),
        ttcWrite: computeStats(writeTimes),
        ttcRead: computeStats(readTimes),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 3: IndexedDB CRUD (Synthetic — equivalente SQLite)
// Equivalente: database locale del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkIndexedDB() {
    const insertTimes = [];
    const readTimes = [];
    const deleteTimes = [];
    const dbName = 'benchmark-idb';

    const preRAM = getMemoryMB();

    for (let iter = 0; iter < CONFIG.iterations; iter++) {
        // Apri/crea DB
        const db = await new Promise((resolve, reject) => {
            const req = indexedDB.open(dbName, 1);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains('records')) {
                    db.createObjectStore('records', { keyPath: 'id' });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });

        // ── INSERT ──
        const t0i = performance.now();
        await new Promise((resolve, reject) => {
            const tx = db.transaction('records', 'readwrite');
            const store = tx.objectStore('records');
            for (let i = 0; i < CONFIG.idbRecords; i++) {
                store.put({ id: i, vehicle: `VEH-${i}`, speed: Math.random() * 200, ts: Date.now() });
            }
            tx.oncomplete = resolve;
            tx.onerror = () => reject(tx.error);
        });
        const t1i = performance.now();
        insertTimes.push(t1i - t0i);

        // ── READ ALL ──
        const t0r = performance.now();
        await new Promise((resolve, reject) => {
            const tx = db.transaction('records', 'readonly');
            const store = tx.objectStore('records');
            const req = store.getAll();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
        const t1r = performance.now();
        readTimes.push(t1r - t0r);

        // ── DELETE ALL ──
        const t0d = performance.now();
        await new Promise((resolve, reject) => {
            const tx = db.transaction('records', 'readwrite');
            const store = tx.objectStore('records');
            const req = store.clear();
            tx.oncomplete = resolve;
            tx.onerror = () => reject(tx.error);
        });
        const t1d = performance.now();
        deleteTimes.push(t1d - t0d);

        db.close();
    }

    // Pulisci DB
    indexedDB.deleteDatabase(dbName);

    const postRAM = getMemoryMB();

    return {
        test: 'IndexedDB CRUD',
        category: 'Synthetic (SQLite)',
        detail: `${CONFIG.idbRecords} record × ${CONFIG.iterations} iter — Insert/Read/Delete`,
        ttc: computeStats(insertTimes.map((ins, i) => ins + readTimes[i] + deleteTimes[i])),
        ttcInsert: computeStats(insertTimes),
        ttcRead: computeStats(readTimes),
        ttcDelete: computeStats(deleteTimes),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 4: Geolocalizzazione (Microbenchmark — Sensore)
// Equivalente: GPS location request del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkGeolocation() {
    if (!navigator.geolocation) {
        return { test: 'Geolocation', category: 'Microbenchmark (Sensore)', error: 'API non supportata' };
    }

    const times = [];
    const preRAM = getMemoryMB();

    for (let i = 0; i < CONFIG.iterations; i++) {
        try {
            const t0 = performance.now();
            await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: CONFIG.geoTimeout,
                    maximumAge: 0     // Forza acquisizione fresca (no cache)
                });
            });
            const t1 = performance.now();
            times.push(t1 - t0);
        } catch (err) {
            return {
                test: 'Geolocation',
                category: 'Microbenchmark (Sensore)',
                error: `Permesso negato o timeout: ${err.message}`,
                completedIterations: i
            };
        }
    }

    const postRAM = getMemoryMB();

    return {
        test: 'Geolocation',
        category: 'Microbenchmark (Sensore)',
        detail: `${CONFIG.iterations} acquisizioni GPS (high accuracy, no cache)`,
        ttc: computeStats(times),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 5: Accelerometro (Microbenchmark — Sensore)
// Equivalente: accelerometer access del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkAccelerometer() {
    // Verifica supporto
    if (!window.DeviceMotionEvent) {
        return { test: 'Accelerometer', category: 'Microbenchmark (Sensore)', error: 'DeviceMotionEvent non supportato' };
    }

    // Su iOS 13+ serve permesso esplicito
    if (typeof DeviceMotionEvent.requestPermission === 'function') {
        try {
            const perm = await DeviceMotionEvent.requestPermission();
            if (perm !== 'granted') {
                return { test: 'Accelerometer', category: 'Microbenchmark (Sensore)', error: 'Permesso negato (iOS)' };
            }
        } catch (err) {
            return { test: 'Accelerometer', category: 'Microbenchmark (Sensore)', error: `Errore permesso: ${err.message}` };
        }
    }

    const preRAM = getMemoryMB();

    const times = [];
    for (let iter = 0; iter < CONFIG.iterations; iter++) {
        const t0 = performance.now();
        await new Promise((resolve) => {
            let count = 0;
            function handler(event) {
                count++;
                if (count >= CONFIG.accelSamples) {
                    window.removeEventListener('devicemotion', handler);
                    resolve();
                }
            }
            window.addEventListener('devicemotion', handler);

            // Timeout di sicurezza (se non arrivano eventi, es. desktop)
            setTimeout(() => {
                window.removeEventListener('devicemotion', handler);
                resolve();
            }, 5000);
        });
        const t1 = performance.now();
        times.push(t1 - t0);
    }

    const postRAM = getMemoryMB();

    // Se tutti i tempi sono ~5000ms, probabilmente siamo su desktop senza sensore
    const allTimedOut = times.every(t => t > 4500);

    if (allTimedOut) {
        return { test: 'Accelerometer', category: 'Microbenchmark (Sensore)', error: 'Nessun evento ricevuto (desktop senza sensore)' };
    }

    return {
        test: 'Accelerometer',
        category: 'Microbenchmark (Sensore)',
        detail: `${CONFIG.accelSamples} campioni × ${CONFIG.iterations} iter`,
        ttc: computeStats(times),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 6: Fetch API / REST Call (Synthetic + E2E Cloud)
// Equivalente: network request + correlazione App Insights
// ══════════════════════════════════════════════════════════════
async function benchmarkFetchAPI() {
    const times = [];
    const preRAM = getMemoryMB();

    // Prova a ottenere il token auth (se su Azure con EasyAuth)
    let authHeaders = {};
    try {
        const authRes = await fetch('/.auth/me');
        if (authRes.ok) {
            const data = await authRes.json();
            if (data && data.length > 0 && data[0].id_token) {
                authHeaders = { 'Authorization': `Bearer ${data[0].id_token}` };
            }
        }
    } catch (e) { /* Dev locale, nessun auth */ }

    for (let i = 0; i < CONFIG.fetchRepetitions; i++) {
        const t0 = performance.now();
        try {
            const res = await fetch(`${API_BASE}/vehicles`, { headers: authHeaders });
            await res.json();
        } catch (err) {
            // Registra comunque il tempo (include timeout/errore)
        }
        const t1 = performance.now();
        times.push(t1 - t0);
    }

    const postRAM = getMemoryMB();

    return {
        test: 'Fetch API (REST)',
        category: 'Synthetic (Network + Cloud)',
        detail: `GET /api/vehicles × ${CONFIG.fetchRepetitions} — E2E con App Insights correlation`,
        ttc: computeStats(times),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.fetchRepetitions
    };
}

// ══════════════════════════════════════════════════════════════
// TEST 7: DOM Stress Test (Synthetic — UI Responsiveness)
// Equivalente: UI rendering / FPS del paper
// ══════════════════════════════════════════════════════════════
async function benchmarkDOMStress() {
    const renderTimes = [];
    const fpsValues = [];
    const container = document.getElementById('dom-stress-container');
    const preRAM = getMemoryMB();

    for (let iter = 0; iter < CONFIG.iterations; iter++) {
        // ── Render: crea N elementi ──
        const t0 = performance.now();
        const fragment = document.createDocumentFragment();
        for (let i = 0; i < CONFIG.domElements; i++) {
            const div = document.createElement('div');
            div.className = 'bench-dom-item';
            div.textContent = `[VEH-${i}] Speed: ${(Math.random() * 200).toFixed(1)} km/h — RPM: ${Math.floor(Math.random() * 8000)}`;
            fragment.appendChild(div);
        }
        container.innerHTML = '';
        container.appendChild(fragment);

        // Forza reflow/repaint
        void container.offsetHeight;
        const t1 = performance.now();
        renderTimes.push(t1 - t0);

        // ── Misura FPS per 500ms ──
        const fps = await new Promise(resolve => {
            let frameCount = 0;
            const startTime = performance.now();
            function countFrame() {
                frameCount++;
                if (performance.now() - startTime < 500) {
                    requestAnimationFrame(countFrame);
                } else {
                    const elapsed = performance.now() - startTime;
                    resolve((frameCount / elapsed) * 1000);
                }
            }
            requestAnimationFrame(countFrame);
        });
        fpsValues.push(fps);

        // Pulisci
        container.innerHTML = '';
        await delay(50);
    }

    const postRAM = getMemoryMB();

    return {
        test: 'DOM Stress Test',
        category: 'Synthetic (UI/FPS)',
        detail: `${CONFIG.domElements} elementi × ${CONFIG.iterations} iter`,
        ttc: computeStats(renderTimes),
        fps: computeStats(fpsValues),
        preRAM: formatMem(preRAM),
        computedRAM: formatMem(preRAM !== null && postRAM !== null ? postRAM - preRAM : null),
        iterations: CONFIG.iterations
    };
}

// ══════════════════════════════════════════════════════════════
// RUNNER: Esegue tutti i test in sequenza
// ══════════════════════════════════════════════════════════════
const allResults = [];

const benchmarks = [
    { id: 'json',     name: 'JSON Processing',  fn: benchmarkJSON },
    { id: 'cache',    name: 'Cache API I/O',     fn: benchmarkCacheAPI },
    { id: 'idb',      name: 'IndexedDB CRUD',    fn: benchmarkIndexedDB },
    { id: 'geo',      name: 'Geolocation',       fn: benchmarkGeolocation },
    { id: 'accel',    name: 'Accelerometer',     fn: benchmarkAccelerometer },
    { id: 'fetch',    name: 'Fetch API (REST)',   fn: benchmarkFetchAPI },
    { id: 'dom',      name: 'DOM Stress Test',    fn: benchmarkDOMStress }
];

function updateStatus(message) {
    const el = document.getElementById('bench-status');
    if (el) el.textContent = message;
}

function updateProgress(current, total) {
    const bar = document.getElementById('progress-fill');
    const text = document.getElementById('progress-text');
    if (bar) bar.style.width = `${(current / total) * 100}%`;
    if (text) text.textContent = `${current} / ${total}`;
}

function addResultRow(result) {
    const tbody = document.getElementById('results-body');
    if (!tbody) return;

    const tr = document.createElement('tr');

    if (result.error) {
        tr.innerHTML = `
            <td>${result.test}</td>
            <td>${result.category}</td>
            <td colspan="5" class="error-cell">⚠️ ${result.error}</td>
        `;
    } else {
        const fpsInfo = result.fps ? `<br><small>FPS: ${result.fps.mean} ± ${result.fps.stdDev}</small>` : '';
        const subTimings = [];
        if (result.ttcWrite) subTimings.push(`W: ${result.ttcWrite.mean}ms`);
        if (result.ttcRead) subTimings.push(`R: ${result.ttcRead.mean}ms`);
        if (result.ttcInsert) subTimings.push(`I: ${result.ttcInsert.mean}ms`);
        if (result.ttcDelete) subTimings.push(`D: ${result.ttcDelete.mean}ms`);
        const subInfo = subTimings.length ? `<br><small>${subTimings.join(' | ')}</small>` : '';

        tr.innerHTML = `
            <td>${result.test}</td>
            <td>${result.category}</td>
            <td class="num">${result.ttc.mean} <small>± ${result.ttc.stdDev}</small>${subInfo}</td>
            <td class="num">${result.ttc.min}</td>
            <td class="num">${result.ttc.max}</td>
            <td class="num">${result.preRAM}</td>
            <td class="num">${result.computedRAM}${fpsInfo}</td>
        `;
    }

    tbody.appendChild(tr);
}

async function runAllBenchmarks() {
    const runBtn = document.getElementById('btn-run');
    const pushBtn = document.getElementById('btn-push');
    runBtn.disabled = true;
    pushBtn.disabled = true;
    allResults.length = 0;
    document.getElementById('results-body').innerHTML = '';

    updateStatus('⏳ Benchmark in corso...');

    for (let i = 0; i < benchmarks.length; i++) {
        const bench = benchmarks[i];
        updateStatus(`▶️ ${bench.name} (${i + 1}/${benchmarks.length})...`);
        updateProgress(i, benchmarks.length);

        // Evidenzia la card attiva
        document.querySelectorAll('.test-card').forEach(c => c.classList.remove('active'));
        const card = document.getElementById(`card-${bench.id}`);
        if (card) card.classList.add('active');

        try {
            const result = await bench.fn();
            allResults.push(result);
            addResultRow(result);
        } catch (err) {
            const errorResult = { test: bench.name, category: 'Errore', error: err.message };
            allResults.push(errorResult);
            addResultRow(errorResult);
        }

        // Rimuovi evidenziazione
        if (card) {
            card.classList.remove('active');
            card.classList.add('done');
        }
    }

    updateProgress(benchmarks.length, benchmarks.length);
    updateStatus('✅ Benchmark completato!');
    runBtn.disabled = false;
    pushBtn.disabled = false;
}

// ══════════════════════════════════════════════════════════════
// PUSH: Invia risultati ad Application Insights
// ══════════════════════════════════════════════════════════════
function pushToAppInsights() {
    if (allResults.length === 0) {
        alert('Nessun risultato da inviare. Esegui prima i benchmark.');
        return;
    }
    if (!window.appInsights) {
        alert('App Insights disabilitato (forse da adblocker/browser privacy settings). Impossibile inviare dati.');
        return;
    }

    const runId = `bench-${Date.now()}`;

    allResults.forEach(result => {
        if (result.error) {
            appInsights.trackEvent({
                name: 'BenchmarkError',
            }, {
                runId,
                test: result.test,
                category: result.category,
                error: result.error
            });
            return;
        }

        // Metrica principale: TTC medio
        appInsights.trackMetric({
            name: `Benchmark_TTC_${result.test.replace(/[^a-zA-Z0-9]/g, '_')}`,
            average: result.ttc.mean,
            min: result.ttc.min,
            max: result.ttc.max,
            sampleCount: result.iterations
        });

        // Evento dettagliato con tutte le proprietà
        const properties = {
            runId,
            test: result.test,
            category: result.category,
            detail: result.detail,
            ttc_mean: String(result.ttc.mean),
            ttc_min: String(result.ttc.min),
            ttc_max: String(result.ttc.max),
            ttc_stdDev: String(result.ttc.stdDev),
            preRAM: result.preRAM,
            computedRAM: result.computedRAM,
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            hardwareConcurrency: String(navigator.hardwareConcurrency || 'N/A'),
            screenResolution: `${screen.width}x${screen.height}`,
            devicePixelRatio: String(window.devicePixelRatio)
        };

        // Aggiungi sub-timing se presenti
        if (result.ttcWrite) properties.ttcWrite_mean = String(result.ttcWrite.mean);
        if (result.ttcRead) properties.ttcRead_mean = String(result.ttcRead.mean);
        if (result.ttcInsert) properties.ttcInsert_mean = String(result.ttcInsert.mean);
        if (result.ttcDelete) properties.ttcDelete_mean = String(result.ttcDelete.mean);
        if (result.fps) {
            properties.fps_mean = String(result.fps.mean);
            properties.fps_stdDev = String(result.fps.stdDev);
        }

        appInsights.trackEvent({ name: 'BenchmarkResult' }, properties);
    });

    // Forza invio immediato
    window.appInsights.flush();

    updateStatus('📤 Risultati inviati ad Application Insights!');
    alert(`✅ ${allResults.length} risultati inviati ad App Insights.\nRun ID: ${runId}\n\nTrovabili in App Insights → Logs → customEvents | customMetrics`);
}

// ── Esponi esplicitamente funzioni per bottone onClick ──
window.runAllBenchmarks = runAllBenchmarks;
window.pushToAppInsights = pushToAppInsights;
