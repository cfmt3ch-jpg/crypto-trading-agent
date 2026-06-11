"""
Web Dashboard API - FastAPI backend for trading dashboard.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from loguru import logger

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not installed. Install with: pip install fastapi uvicorn")


# Pydantic models for API
class TradingStatus(BaseModel):
    running: bool
    uptime: str
    portfolio_value: float
    open_positions: int
    trades_executed: int
    total_pnl: float

class PositionInfo(BaseModel):
    pair: str
    side: str
    amount: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percentage: float

class TradeInfo(BaseModel):
    pair: str
    side: str
    amount: float
    entry_price: float
    exit_price: float
    pnl: float
    timestamp: str

class StrategyInfo(BaseModel):
    name: str
    params: Dict

class ConfigInfo(BaseModel):
    exchange: str
    pairs: List[str]
    timeframe: str
    strategy: str
    risk_per_trade: float
    max_drawdown: float


class TradingDashboard:
    """Web dashboard for monitoring and controlling the trading agent."""
    
    def __init__(self, config: Dict, engine=None):
        self.config = config
        self.engine = engine
        self.app: Optional['FastAPI'] = None
        self.websocket_clients: List['WebSocket'] = []
        self.running = False
    
    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the web dashboard."""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI not available - install fastapi and uvicorn")
            return
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Crypto Trading Agent Dashboard",
            description="API for monitoring and controlling the trading agent",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Setup routes
        self._setup_routes()
        
        # Start server
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        self.running = True
        logger.info(f"Dashboard starting on http://{host}:{port}")
        
        await server.serve()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve dashboard HTML."""
            return self._get_dashboard_html()
        
        @self.app.get("/api/status")
        async def get_status():
            """Get trading status."""
            if not self.engine:
                return {"running": False, "error": "Engine not connected"}
            
            stats = self.engine.get_stats()
            portfolio_stats = self.engine.portfolio.get_stats() if self.engine.portfolio else {}
            
            return {
                "running": self.engine.running,
                "uptime": stats.get("uptime", "0:00:00"),
                "portfolio_value": portfolio_stats.get("total_value", 0),
                "available_balance": portfolio_stats.get("available_balance", 0),
                "open_positions": portfolio_stats.get("open_positions", 0),
                "closed_positions": portfolio_stats.get("closed_positions", 0),
                "trades_executed": stats.get("trades_executed", 0),
                "total_pnl": portfolio_stats.get("total_pnl", 0),
                "win_rate": portfolio_stats.get("win_rate", 0),
                "drawdown": portfolio_stats.get("drawdown", 0)
            }
        
        @self.app.get("/api/positions")
        async def get_positions():
            """Get open positions."""
            if not self.engine or not self.engine.portfolio:
                return {"positions": []}
            
            positions = self.engine.portfolio.get_open_positions()
            
            return {
                "positions": [
                    {
                        "pair": pos.pair,
                        "side": pos.side,
                        "amount": pos.amount,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                        "pnl": pos.unrealized_pnl,
                        "pnl_percentage": pos.unrealized_pnl_percentage
                    }
                    for pos in positions
                ]
            }
        
        @self.app.get("/api/trades")
        async def get_trades():
            """Get trade history."""
            if not self.engine or not self.engine.portfolio:
                return {"trades": []}
            
            trades = self.engine.portfolio.get_closed_positions()
            
            return {
                "trades": [
                    {
                        "pair": trade.pair,
                        "side": trade.side,
                        "amount": trade.amount,
                        "entry_price": trade.entry_price,
                        "exit_price": trade.exit_price,
                        "pnl": trade.final_pnl,
                        "entry_time": trade.entry_time.isoformat(),
                        "exit_time": trade.exit_time.isoformat() if trade.exit_time else None
                    }
                    for trade in trades[-50:]  # Last 50 trades
                ]
            }
        
        @self.app.get("/api/strategy")
        async def get_strategy():
            """Get current strategy."""
            strategy_config = self.config.get("strategy", {})
            return {
                "name": strategy_config.get("name", "unknown"),
                "params": strategy_config.get("params", {})
            }
        
        @self.app.post("/api/strategy/{strategy_name}")
        async def set_strategy(strategy_name: str):
            """Change trading strategy."""
            available = ["sma_crossover", "rsi", "macd", "bollinger_bands"]
            
            if strategy_name not in available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown strategy. Available: {available}"
                )
            
            # Update config
            self.config["strategy"]["name"] = strategy_name
            
            # Reinitialize strategy if engine is running
            if self.engine:
                from src.strategies import get_strategy
                self.engine.strategy = get_strategy(
                    strategy_name, 
                    self.config["strategy"]["params"]
                )
            
            return {"message": f"Strategy changed to {strategy_name}"}
        
        @self.app.post("/api/trading/start")
        async def start_trading():
            """Start trading."""
            if not self.engine:
                raise HTTPException(status_code=400, detail="Engine not available")
            
            if self.engine.running:
                return {"message": "Trading already running"}
            
            import asyncio
            asyncio.create_task(self.engine.start())
            return {"message": "Trading started"}
        
        @self.app.post("/api/trading/stop")
        async def stop_trading():
            """Stop trading."""
            if not self.engine:
                raise HTTPException(status_code=400, detail="Engine not available")
            
            self.engine.stop()
            return {"message": "Trading stopped"}
        
        @self.app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return {
                "exchange": self.config.get("exchange", {}).get("name", "unknown"),
                "pairs": self.config.get("trading", {}).get("pairs", []),
                "timeframe": self.config.get("trading", {}).get("timeframe", "1h"),
                "strategy": self.config.get("strategy", {}).get("name", "unknown"),
                "risk_per_trade": self.config.get("trading", {}).get("risk_per_trade", 0.02),
                "max_drawdown": self.config.get("risk", {}).get("max_drawdown", 0.20),
                "stop_loss": self.config.get("risk", {}).get("stop_loss_pct", 0.05),
                "take_profit": self.config.get("risk", {}).get("take_profit_pct", 0.10)
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: 'WebSocket'):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                while True:
                    # Send updates every second
                    if self.engine:
                        stats = self.engine.get_stats()
                        portfolio_stats = self.engine.portfolio.get_stats() if self.engine.portfolio else {}
                        
                        await websocket.send_json({
                            "type": "update",
                            "data": {
                                "running": self.engine.running,
                                "portfolio_value": portfolio_stats.get("total_value", 0),
                                "open_positions": portfolio_stats.get("open_positions", 0),
                                "total_pnl": portfolio_stats.get("total_pnl", 0),
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                    
                    await asyncio.sleep(1)
                    
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
    
    async def broadcast_update(self, data: Dict):
        """Broadcast update to all WebSocket clients."""
        for client in self.websocket_clients:
            try:
                await client.send_json(data)
            except:
                self.websocket_clients.remove(client)
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Trading Agent Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f23;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { 
            background: linear-gradient(135deg, #1a1a3e, #2d2d6b);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { color: #00d4ff; font-size: 24px; }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        .status-running { background: #00ff88; color: #000; }
        .status-stopped { background: #ff4444; color: #fff; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card {
            background: #1a1a3e;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #2d2d6b;
        }
        .card h2 { 
            color: #00d4ff;
            font-size: 16px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat { 
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #2d2d6b;
        }
        .stat:last-child { border-bottom: none; }
        .stat-label { color: #888; }
        .stat-value { font-weight: bold; }
        .positive { color: #00ff88; }
        .negative { color: #ff4444; }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            margin: 5px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .btn-start { background: #00ff88; color: #000; }
        .btn-stop { background: #ff4444; color: #fff; }
        .btn-strategy { background: #00d4ff; color: #000; }
        
        .positions-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .positions-table th, .positions-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #2d2d6b;
        }
        .positions-table th {
            color: #00d4ff;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .strategy-selector {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .strategy-btn {
            padding: 8px 16px;
            border: 2px solid #2d2d6b;
            background: transparent;
            color: #e0e0e0;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .strategy-btn.active {
            border-color: #00d4ff;
            background: #00d4ff22;
        }
        .strategy-btn:hover {
            border-color: #00d4ff;
        }
        
        #log {
            background: #0a0a1a;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 10px;
        }
        .log-entry { margin: 5px 0; }
        .log-time { color: #666; }
        .log-info { color: #00d4ff; }
        .log-success { color: #00ff88; }
        .log-error { color: #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Crypto Trading Agent</h1>
            <div>
                <span id="status-badge" class="status-badge status-stopped">STOPPED</span>
                <button class="btn btn-start" onclick="startTrading()">▶ Start</button>
                <button class="btn btn-stop" onclick="stopTrading()">⏹ Stop</button>
            </div>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>💰 Portfolio</h2>
                <div class="stat">
                    <span class="stat-label">Total Value</span>
                    <span class="stat-value" id="portfolio-value">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Available Balance</span>
                    <span class="stat-value" id="available-balance">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total P/L</span>
                    <span class="stat-value" id="total-pnl">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Win Rate</span>
                    <span class="stat-value" id="win-rate">0%</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Statistics</h2>
                <div class="stat">
                    <span class="stat-label">Uptime</span>
                    <span class="stat-value" id="uptime">0:00:00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Trades Executed</span>
                    <span class="stat-value" id="trades-executed">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Open Positions</span>
                    <span class="stat-value" id="open-positions">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Max Drawdown</span>
                    <span class="stat-value" id="max-drawdown">0%</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 Strategy</h2>
                <div class="stat">
                    <span class="stat-label">Current Strategy</span>
                    <span class="stat-value" id="current-strategy">-</span>
                </div>
                <div class="strategy-selector">
                    <button class="strategy-btn" onclick="setStrategy('sma_crossover')">SMA</button>
                    <button class="strategy-btn" onclick="setStrategy('rsi')">RSI</button>
                    <button class="strategy-btn" onclick="setStrategy('macd')">MACD</button>
                    <button class="strategy-btn" onclick="setStrategy('bollinger_bands')">BB</button>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>📋 Open Positions</h2>
            <table class="positions-table">
                <thead>
                    <tr>
                        <th>Pair</th>
                        <th>Side</th>
                        <th>Amount</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P/L</th>
                    </tr>
                </thead>
                <tbody id="positions-body">
                    <tr><td colspan="6" style="text-align: center;">No open positions</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>📝 Activity Log</h2>
            <div id="log"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'update') {
                    updateDashboard(data.data);
                }
            };
            
            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateDashboard(data) {
            document.getElementById('portfolio-value').textContent = `$${data.portfolio_value?.toFixed(2) || '0.00'}`;
            document.getElementById('open-positions').textContent = data.open_positions || 0;
            document.getElementById('total-pnl').textContent = `$${data.total_pnl?.toFixed(2) || '0.00'}`;
            
            const badge = document.getElementById('status-badge');
            if (data.running) {
                badge.textContent = 'RUNNING';
                badge.className = 'status-badge status-running';
            } else {
                badge.textContent = 'STOPPED';
                badge.className = 'status-badge status-stopped';
            }
        }
        
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
                document.getElementById('uptime').textContent = data.uptime || '0:00:00';
                document.getElementById('trades-executed').textContent = data.trades_executed || 0;
                document.getElementById('win-rate').textContent = `${(data.win_rate * 100)?.toFixed(1) || 0}%`;
                document.getElementById('max-drawdown').textContent = `${(data.drawdown * 100)?.toFixed(1) || 0}%`;
                document.getElementById('available-balance').textContent = `$${data.available_balance?.toFixed(2) || '0.00'}`;
            } catch (e) {
                console.error('Error fetching status:', e);
            }
        }
        
        async function fetchPositions() {
            try {
                const response = await fetch('/api/positions');
                const data = await response.json();
                const tbody = document.getElementById('positions-body');
                
                if (data.positions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No open positions</td></tr>';
                } else {
                    tbody.innerHTML = data.positions.map(pos => `
                        <tr>
                            <td>${pos.pair}</td>
                            <td>${pos.side.toUpperCase()}</td>
                            <td>${pos.amount.toFixed(4)}</td>
                            <td>$${pos.entry_price.toFixed(2)}</td>
                            <td>$${pos.current_price.toFixed(2)}</td>
                            <td class="${pos.pnl >= 0 ? 'positive' : 'negative'}">$${pos.pnl.toFixed(2)}</td>
                        </tr>
                    `).join('');
                }
            } catch (e) {
                console.error('Error fetching positions:', e);
            }
        }
        
        async function fetchStrategy() {
            try {
                const response = await fetch('/api/strategy');
                const data = await response.json();
                document.getElementById('current-strategy').textContent = data.name;
                
                // Update active button
                document.querySelectorAll('.strategy-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent.toLowerCase().includes(data.name.substring(0, 3))) {
                        btn.classList.add('active');
                    }
                });
            } catch (e) {
                console.error('Error fetching strategy:', e);
            }
        }
        
        async function startTrading() {
            await fetch('/api/trading/start', { method: 'POST' });
            addLog('Trading started', 'success');
        }
        
        async function stopTrading() {
            await fetch('/api/trading/stop', { method: 'POST' });
            addLog('Trading stopped', 'error');
        }
        
        async function setStrategy(name) {
            await fetch(`/api/strategy/${name}`, { method: 'POST' });
            addLog(`Strategy changed to ${name}`, 'info');
            fetchStrategy();
        }
        
        function addLog(message, type = 'info') {
            const log = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            log.innerHTML += `<div class="log-entry"><span class="log-time">[${time}]</span> <span class="log-${type}">${message}</span></div>`;
            log.scrollTop = log.scrollHeight;
        }
        
        // Initialize
        connectWebSocket();
        fetchStatus();
        fetchPositions();
        fetchStrategy();
        
        // Refresh periodically
        setInterval(fetchStatus, 5000);
        setInterval(fetchPositions, 5000);
        setInterval(fetchStrategy, 10000);
        
        addLog('Dashboard initialized', 'success');
    </script>
</body>
</html>
        """
    
    def __repr__(self):
        return f"<TradingDashboard(running={self.running})>"
