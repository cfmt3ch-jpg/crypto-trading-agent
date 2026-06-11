"""
Web Dashboard API - FastAPI backend for trading dashboard with Trade Journal.
"""

import asyncio
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

from src.journal.trade_journal import TradeJournal


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
        
        # Initialize trade journal
        self.journal = TradeJournal("data/journal")
    
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
        
        # ===== TRADE JOURNAL ENDPOINTS =====
        
        @self.app.get("/api/journal")
        async def get_journal(
            pair: Optional[str] = None,
            action: Optional[str] = None,
            strategy: Optional[str] = None,
            limit: int = 50
        ):
            """Get trade journal entries."""
            entries = self.journal.get_entries(
                pair=pair,
                action=action,
                strategy=strategy,
                limit=limit
            )
            
            return {
                "entries": [
                    {
                        "id": e.id,
                        "timestamp": e.timestamp,
                        "pair": e.pair,
                        "side": e.side,
                        "action": e.action,
                        "amount": e.amount,
                        "price": e.price,
                        "total_value": e.total_value,
                        "strategy": e.strategy,
                        "signal_type": e.signal_type,
                        "confidence": e.confidence,
                        "market_trend": e.market_trend,
                        "volatility": e.volatility,
                        "stop_loss": e.stop_loss,
                        "take_profit": e.take_profit,
                        "risk_reward_ratio": e.risk_reward_ratio,
                        "exit_price": e.exit_price,
                        "pnl": e.pnl,
                        "pnl_percentage": e.pnl_percentage,
                        "duration_seconds": e.duration_seconds,
                        "entry_reason": e.entry_reason,
                        "exit_reason": e.exit_reason,
                        "notes": e.notes,
                        "emotions": e.emotions,
                        "tags": e.tags
                    }
                    for e in entries
                ]
            }
        
        @self.app.get("/api/journal/history")
        async def get_trade_history(limit: int = 50):
            """Get complete trade history with open/close pairs."""
            history = self.journal.get_trade_history(limit=limit)
            
            return {
                "trades": [
                    {
                        "id": t["id"],
                        "open": {
                            "timestamp": t["open"].timestamp,
                            "pair": t["open"].pair,
                            "side": t["open"].side,
                            "amount": t["open"].amount,
                            "price": t["open"].price,
                            "strategy": t["open"].strategy,
                            "signal_type": t["open"].signal_type,
                            "confidence": t["open"].confidence,
                            "entry_reason": t["open"].entry_reason,
                            "stop_loss": t["open"].stop_loss,
                            "take_profit": t["open"].take_profit,
                            "risk_reward_ratio": t["open"].risk_reward_ratio
                        } if t["open"] else None,
                        "close": {
                            "timestamp": t["close"].timestamp,
                            "price": t["close"].price,
                            "pnl": t["close"].pnl,
                            "pnl_percentage": t["close"].pnl_percentage,
                            "duration_seconds": t["close"].duration_seconds,
                            "exit_reason": t["close"].exit_reason,
                            "emotions": t["close"].emotions,
                            "notes": t["close"].notes
                        } if t["close"] else None
                    }
                    for t in history
                ]
            }
        
        @self.app.get("/api/journal/stats")
        async def get_journal_stats():
            """Get journal statistics."""
            return self.journal.get_statistics()
        
        @self.app.get("/api/journal/export")
        async def export_journal():
            """Export journal to CSV."""
            filepath = f"data/journal/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.journal.export_to_csv(filepath)
            return {"message": f"Journal exported to {filepath}"}
        
        # ===== WEBSOCKET =====
        
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
        """Generate dashboard HTML with Trade Journal."""
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
        h2 { color: #00d4ff; font-size: 16px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
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
        .btn-journal { background: #9b59b6; color: #fff; }
        
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #2d2d6b;
        }
        th {
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
        
        /* Journal specific styles */
        .journal-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .journal-tab {
            padding: 8px 16px;
            background: #2d2d6b;
            border: none;
            color: #e0e0e0;
            border-radius: 5px;
            cursor: pointer;
        }
        .journal-tab.active {
            background: #00d4ff;
            color: #000;
        }
        .journal-entry {
            background: #0a0a1a;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #2d2d6b;
        }
        .journal-entry.buy { border-left-color: #00ff88; }
        .journal-entry.sell { border-left-color: #ff4444; }
        .journal-entry.profit { border-left-color: #00ff88; }
        .journal-entry.loss { border-left-color: #ff4444; }
        .journal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .journal-pair { font-weight: bold; font-size: 16px; }
        .journal-time { color: #666; font-size: 12px; }
        .journal-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        .journal-detail {
            font-size: 12px;
        }
        .journal-detail-label { color: #888; }
        .journal-detail-value { font-weight: bold; }
        .journal-reason {
            margin-top: 10px;
            padding: 10px;
            background: #1a1a3e;
            border-radius: 5px;
            font-size: 12px;
        }
        .journal-reason-label { color: #00d4ff; margin-bottom: 5px; }
        .confidence-badge {
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: bold;
        }
        .confidence-high { background: #00ff88; color: #000; }
        .confidence-medium { background: #ffaa00; color: #000; }
        .confidence-low { background: #ff4444; color: #fff; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #0a0a1a;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-card-value {
            font-size: 24px;
            font-weight: bold;
            color: #00d4ff;
        }
        .stat-card-label {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
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
        
        <!-- Open Positions -->
        <div class="card" style="margin-top: 20px;">
            <h2>📋 Open Positions</h2>
            <div class="table-container">
                <table>
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
        </div>
        
        <!-- Trade Journal -->
        <div class="card" style="margin-top: 20px;">
            <h2>📔 Trade Journal</h2>
            
            <!-- Journal Stats -->
            <div class="stats-grid" id="journal-stats">
                <div class="stat-card">
                    <div class="stat-card-value" id="journal-total-trades">0</div>
                    <div class="stat-card-label">Total Trades</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-value" id="journal-win-rate">0%</div>
                    <div class="stat-card-label">Win Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-value" id="journal-total-pnl">$0</div>
                    <div class="stat-card-label">Total P/L</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-value" id="journal-avg-pnl">$0</div>
                    <div class="stat-card-label">Avg P/L</div>
                </div>
            </div>
            
            <!-- Journal Tabs -->
            <div class="journal-tabs">
                <button class="journal-tab active" onclick="showJournalTab('all')">All</button>
                <button class="journal-tab" onclick="showJournalTab('opens')">Entries</button>
                <button class="journal-tab" onclick="showJournalTab('closes')">Exits</button>
                <button class="journal-tab" onclick="showJournalTab('history')">Trade History</button>
            </div>
            
            <!-- Journal Entries -->
            <div id="journal-entries"></div>
            
            <!-- Export Button -->
            <button class="btn btn-journal" onclick="exportJournal()" style="margin-top: 15px;">📥 Export Journal</button>
        </div>
        
        <!-- Activity Log -->
        <div class="card" style="margin-top: 20px;">
            <h2>📝 Activity Log</h2>
            <div id="log"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentJournalTab = 'all';
        
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
            
            // Update P/L color
            const pnlElement = document.getElementById('total-pnl');
            pnlElement.className = `stat-value ${(data.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`;
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
        
        async function fetchJournalStats() {
            try {
                const response = await fetch('/api/journal/stats');
                const data = await response.json();
                
                document.getElementById('journal-total-trades').textContent = data.total_trades || 0;
                document.getElementById('journal-win-rate').textContent = `${((data.win_rate || 0) * 100).toFixed(1)}%`;
                document.getElementById('journal-total-pnl').textContent = `$${(data.total_pnl || 0).toFixed(2)}`;
                document.getElementById('journal-avg-pnl').textContent = `$${(data.avg_pnl || 0).toFixed(2)}`;
            } catch (e) {
                console.error('Error fetching journal stats:', e);
            }
        }
        
        async function fetchJournalEntries(tab) {
            try {
                let url = '/api/journal';
                if (tab === 'opens') url += '?action=open';
                else if (tab === 'closes') url += '?action=close';
                else if (tab === 'history') url = '/api/journal/history';
                
                const response = await fetch(url);
                const data = await response.json();
                const container = document.getElementById('journal-entries');
                
                if (tab === 'history') {
                    // Trade history view
                    if (data.trades.length === 0) {
                        container.innerHTML = '<p style="text-align: center; color: #888;">No trade history yet</p>';
                    } else {
                        container.innerHTML = data.trades.map(trade => {
                            const open = trade.open;
                            const close = trade.close;
                            const pnlClass = close && close.pnl >= 0 ? 'profit' : 'loss';
                            
                            return `
                                <div class="journal-entry ${pnlClass}">
                                    <div class="journal-header">
                                        <span class="journal-pair">${open?.pair || 'Unknown'}</span>
                                        <span class="journal-time">${new Date(open?.timestamp).toLocaleString()}</span>
                                    </div>
                                    <div class="journal-details">
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Side</div>
                                            <div class="journal-detail-value">${open?.side?.toUpperCase() || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Amount</div>
                                            <div class="journal-detail-value">${open?.amount?.toFixed(4) || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Entry Price</div>
                                            <div class="journal-detail-value">$${open?.price?.toFixed(2) || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Exit Price</div>
                                            <div class="journal-detail-value">$${close?.price?.toFixed(2) || 'Open'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">P/L</div>
                                            <div class="journal-detail-value ${(close?.pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                                $${close?.pnl?.toFixed(2) || '0.00'}
                                            </div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Strategy</div>
                                            <div class="journal-detail-value">${open?.strategy || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Signal</div>
                                            <div class="journal-detail-value">${open?.signal_type || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Confidence</div>
                                            <div class="journal-detail-value">
                                                <span class="confidence-badge ${(open?.confidence || 0) > 0.7 ? 'confidence-high' : (open?.confidence || 0) > 0.5 ? 'confidence-medium' : 'confidence-low'}">
                                                    ${((open?.confidence || 0) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">R:R Ratio</div>
                                            <div class="journal-detail-value">${open?.risk_reward_ratio?.toFixed(2) || '-'}</div>
                                        </div>
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">Duration</div>
                                            <div class="journal-detail-value">${close?.duration_seconds ? formatDuration(close.duration_seconds) : 'Open'}</div>
                                        </div>
                                    </div>
                                    ${open?.entry_reason ? `
                                        <div class="journal-reason">
                                            <div class="journal-reason-label">📝 Entry Reason</div>
                                            ${open.entry_reason}
                                        </div>
                                    ` : ''}
                                    ${close?.exit_reason ? `
                                        <div class="journal-reason">
                                            <div class="journal-reason-label">📝 Exit Reason</div>
                                            ${close.exit_reason}
                                        </div>
                                    ` : ''}
                                    ${close?.notes ? `
                                        <div class="journal-reason">
                                            <div class="journal-reason-label">💭 Notes</div>
                                            ${close.notes}
                                        </div>
                                    ` : ''}
                                </div>
                            `;
                        }).join('');
                    }
                } else {
                    // Single entries view
                    if (data.entries.length === 0) {
                        container.innerHTML = '<p style="text-align: center; color: #888;">No journal entries yet</p>';
                    } else {
                        container.innerHTML = data.entries.map(entry => `
                            <div class="journal-entry ${entry.side}">
                                <div class="journal-header">
                                    <span class="journal-pair">${entry.pair} - ${entry.action.toUpperCase()}</span>
                                    <span class="journal-time">${new Date(entry.timestamp).toLocaleString()}</span>
                                </div>
                                <div class="journal-details">
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Side</div>
                                        <div class="journal-detail-value">${entry.side.toUpperCase()}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Amount</div>
                                        <div class="journal-detail-value">${entry.amount.toFixed(4)}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Price</div>
                                        <div class="journal-detail-value">$${entry.price.toFixed(2)}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Total Value</div>
                                        <div class="journal-detail-value">$${entry.total_value.toFixed(2)}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Strategy</div>
                                        <div class="journal-detail-value">${entry.strategy || '-'}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Signal</div>
                                        <div class="journal-detail-value">${entry.signal_type || '-'}</div>
                                    </div>
                                    <div class="journal-detail">
                                        <div class="journal-detail-label">Confidence</div>
                                        <div class="journal-detail-value">
                                            <span class="confidence-badge ${entry.confidence > 0.7 ? 'confidence-high' : entry.confidence > 0.5 ? 'confidence-medium' : 'confidence-low'}">
                                                ${(entry.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>
                                    ${entry.pnl !== null ? `
                                        <div class="journal-detail">
                                            <div class="journal-detail-label">P/L</div>
                                            <div class="journal-detail-value ${entry.pnl >= 0 ? 'positive' : 'negative'}">$${entry.pnl.toFixed(2)}</div>
                                        </div>
                                    ` : ''}
                                </div>
                                ${entry.entry_reason ? `
                                    <div class="journal-reason">
                                        <div class="journal-reason-label">📝 Entry Reason</div>
                                        ${entry.entry_reason}
                                    </div>
                                ` : ''}
                                ${entry.exit_reason ? `
                                    <div class="journal-reason">
                                        <div class="journal-reason-label">📝 Exit Reason</div>
                                        ${entry.exit_reason}
                                    </div>
                                ` : ''}
                                ${entry.notes ? `
                                    <div class="journal-reason">
                                        <div class="journal-reason-label">💭 Notes</div>
                                        ${entry.notes}
                                    </div>
                                ` : ''}
                            </div>
                        `).join('');
                    }
                }
            } catch (e) {
                console.error('Error fetching journal:', e);
            }
        }
        
        function formatDuration(seconds) {
            if (seconds < 60) return `${seconds}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
            return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
        }
        
        function showJournalTab(tab) {
            currentJournalTab = tab;
            
            // Update tab buttons
            document.querySelectorAll('.journal-tab').forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.toLowerCase().includes(tab.substring(0, 4))) {
                    btn.classList.add('active');
                }
            });
            
            // Fetch entries
            fetchJournalEntries(tab);
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
        
        async function exportJournal() {
            const response = await fetch('/api/journal/export');
            const data = await response.json();
            addLog(data.message, 'success');
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
        fetchJournalStats();
        fetchJournalEntries('all');
        
        // Refresh periodically
        setInterval(fetchStatus, 5000);
        setInterval(fetchPositions, 5000);
        setInterval(fetchStrategy, 10000);
        setInterval(fetchJournalStats, 10000);
        setInterval(() => fetchJournalEntries(currentJournalTab), 10000);
        
        addLog('Dashboard initialized', 'success');
    </script>
</body>
</html>
        """
    
    def __repr__(self):
        return f"<TradingDashboard(running={self.running})>"
