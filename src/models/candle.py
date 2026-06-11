"""
Candle Model - Represents a candlestick data point.
"""

from datetime import datetime
from dataclasses import dataclass


@dataclass
class Candle:
    """Represents a single candlestick."""
    
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)."""
        return self.close < self.open
    
    @property
    def body_size(self) -> float:
        """Calculate body size (absolute difference between open and close)."""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Calculate upper shadow size."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Calculate lower shadow size."""
        return min(self.open, self.close) - self.low
    
    @property
    def range(self) -> float:
        """Calculate total range (high - low)."""
        return self.high - self.low
    
    @property
    def typical_price(self) -> float:
        """Calculate typical price (HLC/3)."""
        return (self.high + self.low + self.close) / 3
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Candle':
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data["volume"])
        )
    
    def __repr__(self):
        return (
            f"<Candle("
            f"timestamp={self.timestamp}, "
            f"open={self.open}, "
            f"high={self.high}, "
            f"low={self.low}, "
            f"close={self.close}, "
            f"volume={self.volume})>"
        )
