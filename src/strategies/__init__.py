"""
Trading strategies.
"""

from src.strategies.base import BaseStrategy, Signal, SignalSide
from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi import RSIStrategy
from src.strategies.macd import MACDStrategy
from src.strategies.bollinger_bands import BollingerBandsStrategy

__all__ = [
    "BaseStrategy",
    "Signal",
    "SignalSide",
    "SMACrossoverStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerBandsStrategy"
]

# Strategy registry
STRATEGIES = {
    "sma_crossover": SMACrossoverStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger_bands": BollingerBandsStrategy
}

def get_strategy(name: str, params: dict) -> BaseStrategy:
    """Get strategy by name."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name](params)
