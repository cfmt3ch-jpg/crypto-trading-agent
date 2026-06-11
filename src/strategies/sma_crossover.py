"""
SMA Crossover Strategy - Simple Moving Average crossover trading strategy.
"""

from typing import Dict, List, Optional

import numpy as np

from src.strategies.base import BaseStrategy, Signal, SignalSide
from src.models.candle import Candle


class SMACrossoverStrategy(BaseStrategy):
    """Simple Moving Average crossover strategy.
    
    Buy when short SMA crosses above long SMA.
    Sell when short SMA crosses below long SMA.
    """
    
    def __init__(self, params: Dict):
        super().__init__(params)
        self.short_period = params.get("short_period", 20)
        self.long_period = params.get("long_period", 50)
        self.stop_loss_pct = params.get("stop_loss_pct", 0.05)
        self.take_profit_pct = params.get("take_profit_pct", 0.10)
    
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        """Generate trading signal based on SMA crossover."""
        if len(candles) < self.long_period:
            return None
        
        # Calculate SMAs
        closes = [c.close for c in candles]
        short_sma = self._calculate_sma(closes, self.short_period)
        long_sma = self._calculate_sma(closes, self.long_period)
        
        # Check for crossover
        if len(short_sma) < 2 or len(long_sma) < 2:
            return None
        
        # Current values
        current_short = short_sma[-1]
        current_long = long_sma[-1]
        previous_short = short_sma[-2]
        previous_long = long_sma[-2]
        
        # Current price
        current_price = candles[-1].close
        
        # Bullish crossover: short SMA crosses above long SMA
        if previous_short <= previous_long and current_short > current_long:
            return Signal(
                side=SignalSide.BUY,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.BUY, self.stop_loss_pct
                ),
                take_profit=self.calculate_take_profit(
                    current_price, SignalSide.BUY, self.take_profit_pct
                ),
                confidence=self._calculate_confidence(
                    short_sma, long_sma, "bullish"
                ),
                metadata={
                    "short_sma": current_short,
                    "long_sma": current_long,
                    "crossover_type": "bullish"
                }
            )
        
        # Bearish crossover: short SMA crosses below long SMA
        elif previous_short >= previous_long and current_short < current_long:
            return Signal(
                side=SignalSide.SELL,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.SELL, self.stop_loss_pct
                ),
                take_profit=self.calculate_take_profit(
                    current_price, SignalSide.SELL, self.take_profit_pct
                ),
                confidence=self._calculate_confidence(
                    short_sma, long_sma, "bearish"
                ),
                metadata={
                    "short_sma": current_short,
                    "long_sma": current_long,
                    "crossover_type": "bearish"
                }
            )
        
        # No signal
        return None
    
    def _calculate_sma(self, data: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average."""
        if len(data) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            sma.append(sum(window) / period)
        
        return sma
    
    def _calculate_confidence(
        self, 
        short_sma: List[float], 
        long_sma: List[float], 
        crossover_type: str
    ) -> float:
        """Calculate confidence level for the signal."""
        if len(short_sma) < 2 or len(long_sma) < 2:
            return 0.5
        
        # Calculate SMA difference
        current_diff = abs(short_sma[-1] - long_sma[-1])
        previous_diff = abs(short_sma[-2] - long_sma[-2])
        
        # Higher confidence if SMA divergence is increasing
        if current_diff > previous_diff:
            confidence = min(0.8, 0.5 + (current_diff / long_sma[-1]) * 10)
        else:
            confidence = max(0.3, 0.5 - (current_diff / long_sma[-1]) * 5)
        
        # Adjust based on trend strength
        if crossover_type == "bullish":
            # Check if short SMA is trending up
            if short_sma[-1] > short_sma[-2]:
                confidence = min(0.9, confidence + 0.1)
        else:
            # Check if short SMA is trending down
            if short_sma[-1] < short_sma[-2]:
                confidence = min(0.9, confidence + 0.1)
        
        return confidence
    
    def __repr__(self):
        return (
            f"<SMACrossoverStrategy("
            f"short={self.short_period}, "
            f"long={self.long_period})>"
        )
