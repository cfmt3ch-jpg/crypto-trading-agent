# Crypto Trading Agent

An autonomous AI-powered cryptocurrency trading agent.

## Features

- Multi-exchange support (Binance, Bybit, OKX)
- AI-powered trading strategies
- Risk management system
- Real-time monitoring
- Backtesting capabilities
- Paper trading mode

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `config/config.example.yaml` to `config/config.yaml` and configure your settings.

## Usage

```bash
# Run trading agent
python -m src.main

# Run backtest
python -m src.backtest --strategy sma_crossover --pair BTC/USDT

# Run API server
python -m src.api.server
```

## License

MIT License
