# 🤖 Crypto Trading Agent

An autonomous AI-powered cryptocurrency trading agent with multi-exchange support, advanced strategies, web dashboard, and Telegram bot integration.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

## 📸 Dashboard Preview

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Crypto Trading Agent                    [RUNNING] ▶ ⏹  │
├─────────────────────────────────────────────────────────────┤
│  💰 Portfolio          │  📊 Statistics        │  📈 Strategy│
│  ────────────────      │  ────────────────     │  ──────────│
│  Total Value: $10,500  │  Uptime: 2h 30m       │  Current:  │
│  Available: $5,000     │  Trades: 15           │  SMA Cross │
│  P/L: +$500            │  Positions: 3         │            │
│  Win Rate: 66.7%       │  Drawdown: 2.1%       │  [SMA][RSI]│
│                        │                       │  [MACD][BB]│
├─────────────────────────────────────────────────────────────┤
│  📋 Open Positions                                          │
│  ─────────────────────────────────────────────────────────  │
│  BTC/USDT │ LONG │ 0.1 │ $50,000 │ $51,200 │ +$120 🟢    │
│  ETH/USDT │ LONG │ 1.0 │ $3,000  │ $3,050  │ +$50 🟢     │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🔄 Multi-Exchange Support
- **Binance** - Spot & Futures trading
- **Hyperliquid** - DEX Perpetuals trading
- **Paper Trading** - Simulated trading for testing

### 📈 Trading Strategies
| Strategy | Type | Description |
|----------|------|-------------|
| **SMA Crossover** | Trend Following | Buy/sell on moving average crossovers |
| **RSI** | Mean Reversion | Trade oversold/overbought conditions |
| **MACD** | Momentum | Trade momentum shifts |
| **Bollinger Bands** | Mean Reversion | Trade band bounces |

### 🛡️ Risk Management
- Position sizing based on risk percentage
- Stop-loss & take-profit orders
- Maximum drawdown protection
- Maximum open positions limit
- Minimum trade amount

### 🌐 Web Dashboard
- Real-time portfolio monitoring
- Live position tracking
- Strategy switching
- Start/Stop trading controls
- WebSocket updates
- Dark theme UI

### 🤖 Telegram Bot
- Remote monitoring & control
- Trade notifications
- Position updates
- Strategy management
- Authorized users support

### 📝 Paper Trading
- Simulated exchange
- No real money at risk
- Fee & slippage simulation
- Performance statistics
- Strategy testing

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/cfmt3ch-jpg/crypto-trading-agent.git
cd crypto-trading-agent
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit configuration
nano config/config.yaml
```

### 4. Run

```bash
# Run trading agent
python -m src.main

# Run dashboard only
python -m src.dashboard.server

# Run telegram bot only
python -m src.bot.telegram_bot
```

---

## ⚙️ Configuration

### Exchange Configuration

```yaml
exchange:
  name: binance  # binance, hyperliquid, paper_trading
  api_key: ${EXCHANGE_API_KEY}
  api_secret: ${EXCHANGE_API_SECRET}
  testnet: true  # Use testnet for testing
```

### Trading Configuration

```yaml
trading:
  pairs:
    - BTC/USDT
    - ETH/USDT
  timeframe: 1h  # 1m, 5m, 15m, 1h, 4h, 1d
  max_positions: 5
  risk_per_trade: 0.02  # 2% of portfolio
```

### Strategy Configuration

```yaml
strategy:
  name: sma_crossover  # sma_crossover, rsi, macd, bollinger_bands
  params:
    # SMA Crossover
    short_period: 20
    long_period: 50
    
    # RSI
    rsi_period: 14
    oversold: 30
    overbought: 70
    
    # MACD
    fast_period: 12
    slow_period: 26
    signal_period: 9
    
    # Bollinger Bands
    period: 20
    std_dev: 2.0
```

### Risk Management

```yaml
risk:
  stop_loss_pct: 0.05  # 5%
  take_profit_pct: 0.10  # 10%
  max_drawdown: 0.20  # 20%
  max_open_trades: 3
```

### Telegram Bot

```yaml
notifications:
  enabled: true
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
    authorized_users:
      - 123456789  # Your Telegram user ID
```

### Web Dashboard

```yaml
api:
  enabled: true
  host: 0.0.0.0
  port: 8000
```

---

## 📁 Project Structure

```
crypto-trading-agent/
├── src/
│   ├── core/
│   │   ├── engine.py           # Main trading engine
│   │   ├── portfolio.py        # Portfolio management
│   │   └── order_manager.py    # Order execution
│   ├── strategies/
│   │   ├── base.py             # Base strategy class
│   │   ├── sma_crossover.py    # SMA Crossover strategy
│   │   ├── rsi.py              # RSI strategy
│   │   ├── macd.py             # MACD strategy
│   │   └── bollinger_bands.py  # Bollinger Bands strategy
│   ├── exchanges/
│   │   ├── base.py             # Base exchange class
│   │   ├── binance.py          # Binance integration
│   │   ├── hyperliquid.py      # Hyperliquid DEX
│   │   └── paper_trading.py    # Paper trading
│   ├── models/
│   │   ├── candle.py           # Candlestick data
│   │   ├── order.py            # Order model
│   │   ├── position.py         # Position tracking
│   │   └── trade.py            # Trade history
│   ├── bot/
│   │   └── telegram_bot.py     # Telegram bot
│   ├── dashboard/
│   │   └── server.py           # Web dashboard
│   └── utils/
│       ├── config.py           # Configuration loader
│       └── logger.py           # Logging setup
├── config/
│   └── config.example.yaml     # Example configuration
├── data/
│   ├── historical/             # Historical data
│   └── cache/                  # Cache files
├── logs/                       # Log files
├── models/                     # ML models
├── tests/                      # Test files
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── README.md
├── requirements.txt
├── LICENSE
└── .gitignore
```

---

## 🎯 Usage Examples

### Paper Trading (Recommended for Testing)

```yaml
# config/config.yaml
exchange:
  name: paper_trading
  initial_balance: 10000
```

```bash
python -m src.main
```

### Binance Trading

```yaml
# config/config.yaml
exchange:
  name: binance
  api_key: your_api_key
  api_secret: your_api_secret
  testnet: true  # Set to false for live trading
```

```bash
python -m src.main
```

### Hyperliquid Trading

```yaml
# config/config.yaml
exchange:
  name: hyperliquid
  api_key: your_wallet_address
  api_secret: your_private_key
  testnet: true
```

```bash
python -m src.main
```

### Web Dashboard

```bash
# Start dashboard
python -m src.dashboard.server

# Open in browser
# http://localhost:8000
```

### Telegram Bot

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id

# Start bot
python -m src.bot.telegram_bot
```

---

## 📊 Trading Strategies

### SMA Crossover
Simple Moving Average crossover strategy.
- **Buy Signal:** Short SMA crosses above Long SMA
- **Sell Signal:** Short SMA crosses below Long SMA
- **Best For:** Trending markets

### RSI (Relative Strength Index)
Mean reversion strategy based on momentum.
- **Buy Signal:** RSI crosses above oversold level (30)
- **Sell Signal:** RSI crosses below overbought level (70)
- **Best For:** Ranging markets

### MACD (Moving Average Convergence Divergence)
Momentum strategy using EMA crossovers.
- **Buy Signal:** MACD crosses above signal line
- **Sell Signal:** MACD crosses below signal line
- **Best For:** Trend confirmation

### Bollinger Bands
Mean reversion strategy using volatility bands.
- **Buy Signal:** Price bounces off lower band
- **Sell Signal:** Price bounces off upper band
- **Best For:** Volatile markets

---

## 🛡️ Risk Management

### Position Sizing
```python
position_size = (portfolio_value * risk_per_trade) / (entry_price - stop_loss)
```

### Stop Loss
- Automatic stop-loss based on percentage
- Trailing stop option available

### Take Profit
- Automatic take-profit based on percentage
- Risk-reward ratio optimization

### Maximum Drawdown
- Automatic position closure when drawdown exceeded
- Trading halted until manual restart

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_strategy.py
```

---

## 📈 Performance Metrics

The agent tracks:
- Total P/L (Profit/Loss)
- Win Rate
- Maximum Drawdown
- Sharpe Ratio
- Trade Count
- Average Trade Duration

---

## 🔧 API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Trading status |
| `/api/positions` | GET | Open positions |
| `/api/trades` | GET | Trade history |
| `/api/strategy` | GET | Current strategy |
| `/api/strategy/{name}` | POST | Change strategy |
| `/api/trading/start` | POST | Start trading |
| `/api/trading/stop` | POST | Stop trading |
| `/api/config` | GET | Current config |

### WebSocket

```
ws://localhost:8000/ws
```

Real-time updates every second:
```json
{
  "type": "update",
  "data": {
    "running": true,
    "portfolio_value": 10500.00,
    "open_positions": 3,
    "total_pnl": 500.00,
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

---

## 🤖 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |
| `/status` | Trading status |
| `/balance` | Account balance |
| `/positions` | Open positions |
| `/trades` | Recent trades |
| `/start_trading` | Start trading |
| `/stop_trading` | Stop trading |
| `/strategy [name]` | Change strategy |
| `/stats` | Trading statistics |
| `/config` | Show config |

---

## 📝 Environment Variables

```bash
# Exchange API Keys
EXCHANGE_API_KEY=your_api_key
EXCHANGE_API_SECRET=your_api_secret

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
CONFIG_PATH=config/config.yaml
LOG_LEVEL=INFO
```

---

## 🗺️ Roadmap

- [x] Multi-exchange support
- [x] Multiple trading strategies
- [x] Web dashboard
- [x] Telegram bot
- [x] Paper trading
- [ ] Backtesting module
- [ ] ML-based strategies
- [ ] Portfolio rebalancing
- [ ] More exchanges (OKX, Bybit)
- [ ] Mobile app
- [ ] Social trading

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Cryptocurrency trading involves substantial risk of loss
- Past performance is not indicative of future results
- Never trade with money you cannot afford to lose
- Always test with paper trading first
- Use at your own risk

---

## 🙏 Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency trading library
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram bot framework
- [Hyperliquid](https://hyperliquid.xyz/) - DEX protocol

---

## 📞 Support

- 📧 Email: cfm.t3ch@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/cfmt3ch-jpg/crypto-trading-agent/issues)
- 📖 Docs: [Documentation](https://github.com/cfmt3ch-jpg/crypto-trading-agent/tree/main/docs)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/cfmt3ch-jpg">cfmt3ch-jpg</a>
</p>
