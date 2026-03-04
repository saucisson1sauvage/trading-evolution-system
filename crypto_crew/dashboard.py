import os
import json
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Paths
BASE_DIR = "/home/saus/crypto_crew"
HISTORY_JSON = f"{BASE_DIR}/gen_history.json"
LIVE_THINKING = f"{BASE_DIR}/ai_thinking.live"
AGENT_LOG = f"{BASE_DIR}/agent_crew.log"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Crew | Command Center</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root { --bg: #0a0a0b; --panel: #141417; --accent: #00ff41; --text: #e0e0e0; --border: #2d2d33; --hover: #1c1c21; --loss: #ff4141; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', -apple-system, sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* SIDEBAR */
        nav { width: 260px; background: var(--panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 10; }
        .nav-header { padding: 25px; font-weight: bold; border-bottom: 1px solid var(--border); color: var(--accent); display: flex; justify-content: space-between; }
        .gen-list { flex-grow: 1; overflow-y: auto; padding: 10px 0; }
        .gen-item { padding: 12px 25px; cursor: pointer; border-left: 3px solid transparent; font-size: 0.9em; transition: 0.2s; display: flex; justify-content: space-between; }
        .gen-item:hover { background: var(--hover); }
        .gen-item.active { border-color: var(--accent); background: #1a1a1f; color: var(--accent); }
        
        /* MAIN */
        main { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; background: #0d0d0f; }
        .top-bar { padding: 15px 30px; background: var(--panel); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .content-scroll { flex-grow: 1; overflow-y: auto; padding: 30px; }
        
        /* DASHBOARD GRID */
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
        .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .card-2 { grid-column: span 2; }
        .card-4 { grid-column: span 4; }
        
        h3 { margin-top: 0; font-size: 0.75em; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 15px; }
        .stat-big { font-size: 2.2em; font-weight: bold; color: var(--accent); }
        .stat-label { font-size: 0.8em; color: #555; margin-top: 5px; }
        
        /* EXIT BARS */
        .exit-row { margin-bottom: 15px; }
        .exit-info { display: flex; justify-content: space-between; font-size: 0.8em; margin-bottom: 5px; }
        .exit-bar { height: 6px; background: #222; border-radius: 3px; overflow: hidden; }
        .exit-fill { height: 100%; background: var(--accent); border-radius: 3px; }
        .exit-fill.loss { background: var(--loss); }

        /* LOGS */
        pre { background: #000; padding: 20px; border-radius: 10px; font-family: 'Fira Code', monospace; font-size: 0.85em; color: #00ff41; border: 1px solid #111; line-height: 1.6; margin: 0; }
        
        /* MARKDOWN STYLING */
        .markdown-body { color: #bbb; line-height: 1.6; font-size: 0.95em; }
        .markdown-body h1, .markdown-body h2, .markdown-body h3 { color: #fff; margin-top: 20px; margin-bottom: 10px; }
        .markdown-body code { background: #1a1a1f; padding: 2px 5px; border-radius: 4px; font-family: monospace; color: var(--accent); }
        .markdown-body ul { padding-left: 20px; }
        .markdown-body li { margin-bottom: 8px; }

        .tabs { display: flex; gap: 10px; margin-bottom: 25px; }
        .tab-btn { padding: 10px 20px; border-radius: 30px; border: 1px solid var(--border); background: none; color: var(--text); cursor: pointer; font-size: 0.85em; transition: 0.2s; }
        .tab-btn:hover { border-color: #555; }
        .tab-btn.active { background: var(--accent); color: #000; border-color: var(--accent); font-weight: bold; }
    </style>
</head>
<body>
    <nav>
        <div class="nav-header"><span>GENERATIONS</span> <span id="genCount" style="opacity:0.4">0</span></div>
        <div id="genList" class="gen-list"></div>
    </nav>
    
    <main>
        <div class="top-bar">
            <div id="genTitle" style="font-weight: 600; font-size: 1.1em; color: #fff;">Synchronizing DNA...</div>
            <div id="lastUpdate" style="opacity: 0.4; font-size: 0.75em;"></div>
        </div>
        
        <div class="content-scroll">
            <div class="tabs">
                <button class="tab-btn active" id="tab-stats" onclick="setView('stats')">Post-Mortem Analysis</button>
                <button class="tab-btn" id="tab-thinking" onclick="setView('thinking')">AI Thinking</button>
                <button class="tab-btn" id="tab-logs" onclick="setView('logs')">Live Bot Output</button>
            </div>

            <div id="viewStats">
                <div class="grid">
                    <div class="card card-2">
                        <h3>Evolutionary Profit Curve</h3>
                        <div style="height: 200px;"><canvas id="profitChart"></canvas></div>
                    </div>
                    <div class="card">
                        <h3>Core Performance</h3>
                        <div id="winnerProfit" class="stat-big">0.0%</div>
                        <div id="winnerCAGR" class="stat-label">CAGR: 0.0%</div>
                        <div id="winnerTrades" class="stat-label">Total Trades: 0</div>
                    </div>
                    <div class="card">
                        <h3>Risk & Alpha</h3>
                        <div id="winnerSharpe" class="stat-big" style="color:#4141ff">0.0</div>
                        <div class="stat-label">Sharpe Ratio</div>
                        <div id="winnerDD" class="stat-label" style="color:var(--loss)">Drawdown: -0.0%</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Trade Dynamics</h3>
                        <div id="winnerWinrate" class="stat-big">0%</div>
                        <div class="stat-label">Win Rate</div>
                        <div id="winnerLS" class="stat-label">Long/Short: 0/0</div>
                    </div>
                    <div class="card card-2">
                        <h3>Exit Reason Breakdown</h3>
                        <div id="exitStats"></div>
                    </div>
                    <div class="card">
                        <h3>Time Analysis</h3>
                        <div id="winnerDur" class="stat-big" style="font-size: 1.5em; margin-top: 10px;">0:00</div>
                        <div class="stat-label">Avg Trade Duration</div>
                    </div>
                </div>
                
                <div class="card card-4">
                    <h3>AI Reasoning & Reflection</h3>
                    <div id="genThinking" class="markdown-body"></div>
                </div>
            </div>

            <div id="viewThinking" style="display:none;">
                <pre id="thinkingPre"></pre>
            </div>

            <div id="viewLogs" style="display:none;">
                <pre id="logsPre"></pre>
            </div>
        </div>
    </main>

    <script>
        let fullData = [];
        let currentGen = 0;
        let charts = {};

        async function refresh() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                if (data.history && data.history.length !== fullData.length) {
                    fullData = data.history;
                    document.getElementById('genCount').innerText = fullData.length;
                    renderGenList();
                    if (currentGen === 0 && fullData.length > 0) selectGen(fullData[fullData.length-1].gen);
                }
                
                if (data.thinking) document.getElementById('thinkingPre').innerText = data.thinking;
                if (data.agent) document.getElementById('logsPre').innerText = data.agent;
                document.getElementById('lastUpdate').innerText = "Last Heartbeat: " + new Date().toLocaleTimeString();
                
                updateWinnerView();
                updateMainChart();
            } catch (e) { console.error("Data sync failed", e); }
        }

        function getMetric(genData, key, fallback = "N/A") {
            if (!genData) return fallback;
            if (genData.metrics && genData.metrics[key] !== undefined) return genData.metrics[key];
            if (genData.winner && genData.winner[key] !== undefined) return genData.winner[key];
            if (key === 'profit_pct' && genData.winner && genData.winner.profit !== undefined) return genData.winner.profit;
            if (key === 'win_rate' && genData.metrics && genData.metrics.winrate !== undefined) return genData.metrics.winrate;
            return fallback;
        }

        function renderGenList() {
            const container = document.getElementById('genList');
            container.innerHTML = fullData.map(g => {
                const profit = getMetric(g, 'profit_pct', 0);
                return `
                <div class="gen-item ${g.gen === currentGen ? 'active' : ''}" onclick="selectGen(${g.gen})">
                    <span>Gen ${g.gen}</span>
                    <span style="opacity:0.5">${typeof profit === 'number' ? profit.toFixed(1) : profit}%</span>
                </div>
            `}).reverse().join('');
        }

        function selectGen(gen) {
            currentGen = gen;
            renderGenList();
            updateWinnerView();
            document.getElementById('genTitle').innerText = "GENERATION " + gen + " DETAILED REPORT";
        }

        function updateWinnerView() {
            const data = fullData.find(g => g.gen === currentGen);
            if (!data) return;
            
            const profit = getMetric(data, 'profit_pct', 0);
            const trades = getMetric(data, 'trades', 0);
            const winrate = getMetric(data, 'win_rate', 0);
            const sharpe = getMetric(data, 'sharpe', 0);
            const drawdown = getMetric(data, 'drawdown', 0);
            const cagr = getMetric(data, 'cagr', "0.0");
            const long_short = getMetric(data, 'long_short', "0/0");
            const duration = getMetric(data, 'avg_duration', "0:00");
            const exits = getMetric(data, 'exits', {});

            document.getElementById('winnerProfit').innerText = (typeof profit === 'number' ? profit.toFixed(2) : profit) + "%";
            document.getElementById('winnerCAGR').innerText = "CAGR: " + cagr + "%";
            document.getElementById('winnerTrades').innerText = "Total Trades: " + trades;
            document.getElementById('winnerWinrate').innerText = winrate + "%";
            document.getElementById('winnerSharpe').innerText = (typeof sharpe === 'number' ? sharpe.toFixed(2) : sharpe);
            document.getElementById('winnerDD').innerText = "Max Drawdown: -" + (typeof drawdown === 'number' ? drawdown.toFixed(2) : drawdown) + "%";
            document.getElementById('winnerLS').innerText = "Long/Short: " + long_short;
            document.getElementById('winnerDur').innerText = duration;
            
            // RENDER MARKDOWN
            document.getElementById('genThinking').innerHTML = marked.parse(data.thinking || "No analysis available.");
            
            const total = trades || 1;
            document.getElementById('exitStats').innerHTML = Object.entries(exits).map(([k, v]) => `
                <div class="exit-row">
                    <div class="exit-info"><span>${k.replace(/_/g, ' ').toUpperCase()}</span><span>${v} (${((v/total)*100).toFixed(0)}%)</span></div>
                    <div class="exit-bar"><div class="exit-fill ${k.includes('loss')?'loss':''}" style="width:${(v/total)*100}%"></div></div>
                </div>
            `).join('') || "No exit data recorded.";
        }

        function setView(v) {
            document.getElementById('viewStats').style.display = v === 'stats' ? 'block' : 'none';
            document.getElementById('viewThinking').style.display = v === 'thinking' ? 'block' : 'none';
            document.getElementById('viewLogs').style.display = v === 'logs' ? 'block' : 'none';
            document.getElementById('tab-stats').classList.toggle('active', v === 'stats');
            document.getElementById('tab-thinking').classList.toggle('active', v === 'thinking');
            document.getElementById('tab-logs').classList.toggle('active', v === 'logs');
        }

        function updateMainChart() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            const labels = fullData.map(g => 'G' + g.gen);
            const profits = fullData.map(g => getMetric(g, 'profit_pct', 0));

            if (charts.main) charts.main.destroy();
            charts.main = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        data: profits,
                        borderColor: '#00ff41',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        backgroundColor: 'rgba(0, 255, 65, 0.05)',
                        pointBackgroundColor: '#00ff41',
                        pointRadius: 3
                    }]
                },
                options: { 
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { 
                        y: { grid: { color: '#1a1a1f' }, ticks: { color: '#555' } },
                        x: { grid: { display: false }, ticks: { color: '#555' } }
                    }
                }
            });
        }

        setInterval(refresh, 5000);
        refresh();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    def read_last_kb(path, kb=100):
        if not os.path.exists(path): return "Waiting for agent to initialize file..."
        try:
            with open(path, 'rb') as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - kb*1024))
                content = f.read().decode('utf-8', errors='ignore')
                # FILTER OUT LLAMA SPAM
                lines = [l for l in content.split('\n') if "llama_context" not in l and "llama_model_loader" not in l]
                return '\n'.join(lines)
        except: return "Error reading file."

    history = []
    if os.path.exists(HISTORY_JSON):
        try:
            with open(HISTORY_JSON, 'r') as f:
                history = json.load(f)
        except: pass

    return jsonify({
        "thinking": read_last_kb(LIVE_THINKING, 50),
        "agent": read_last_kb(AGENT_LOG, 50),
        "history": history
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
