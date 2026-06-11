"""
Base Strategy - Abstract base class for trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.models.candle import Candle


class SignalSide(Enum):
    """Trading signal side."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    """Trading signal."""
    side: SignalSide
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_valid(self) -> bool:
        """Check if signal is valid."""
        return self.side != SignalSide.HOLD and self.confidence > 0.5


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, params: Dict):
        self.params = params
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        """Generate trading signal from candle data."""
        pass
    
    def calculate_stop_loss(
        self, 
        entry_price: float, 
        side: SignalSide, 
        percentage: float = 0.05
    ) -> float:
        """Calculate stop loss price."""
        if side == SignalSide.BUY:
            return entry_price * (1 - percentage)
        else:
            return entry_price * (1 + percentage)
    
    def calculate_take_profit(
        self, 
        entry_price: float, 
        side: SignalSide, 
        percentage: float = 0.10
    ) -> float:
        """Calculate take profit price."""
        if side == SignalSide.BUY:
            return entry_price * (1 + percentage)
        else:
            return entry_price * (1 - percentage)
    
    def __repr__(self):
        return f"<{self.name}(params={self.params})>"
