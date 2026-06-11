"""
RSI Strategy - Relative Strength Index trading strategy.
"""

from typing import Dict, List, Optional

import numpy as np

from src.strategies.base import BaseStrategy, Signal, SignalSide
from src.models.candle import Candle


class RSIStrategy(BaseStrategy):
    """Relative Strength Index strategy.
    
    Buy when RSI crosses above oversold level (default 30).
    Sell when RSI crosses below overbought level (default 70).
    """
    
    def __init__(self, params: Dict):
        super().__init__(params)
        self.rsi_period = params.get("rsi_period", 14)
        self.oversold = params.get("oversold", 30)
        self.overbought = params.get("overbought", 70)
        self.stop_loss_pct = params.get("stop_loss_pct", 0.05)
        self.take_profit_pct = params.get("take_profit_pct", 0.10)
    
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        """Generate trading signal based on RSI."""
        if len(candles) < self.rsi_period + 1:
            return None
        
        # Calculate RSI
        closes = [c.close for c in candles]
        rsi_values = self._calculate_rsi(closes, self.rsi_period)
        
        if len(rsi_values) < 2:
            return None
        
        # Current and previous RSI
        current_rsi = rsi_values[-1]
        previous_rsi = rsi_values[-2]
        
        # Current price
        current_price = candles[-1].close
        
        # Buy signal: RSI crosses above oversold level
        if previous_rsi <= self.oversold and current_rsi > self.oversold:
            return Signal(
                side=SignalSide.BUY,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.BUY, self.stop_loss_pct
                ),
                take_profit=self.calculate_take_profit(
                    current_price, SignalSide.BUY, self.take_profit_pct
                ),
                confidence=self._calculate_confidence(current_rsi, "oversold"),
                metadata={
                    "rsi": current_rsi,
                    "previous_rsi": previous_rsi,
                    "signal_type": "oversold_recovery"
                }
            )
        
        # Sell signal: RSI crosses below overbought level
        elif previous_rsi >= self.overbought and current_rsi < self.overbought:
            return Signal(
                side=SignalSide.SELL,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.SELL, self.stop_loss_pct
                ),
                take_profit=self.calculate_take_profit(
                    current_price, SignalSide.SELL, self.take_profit_pct
                ),
                confidence=self._calculate_confidence(current_rsi, "overbought"),
                metadata={
                    "rsi": current_rsi,
                    "previous_rsi": previous_rsi,
                    "signal_type": "overbought_reversal"
                }
            )
        
        # No signal
        return None
    
    def _calculate_rsi(self, data: List[float], period: int) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(data) < period + 1:
            return []
        
        # Calculate price changes
        deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
        
        # Calculate gains and losses
        gains = [max(0, delta) for delta in deltas]
        losses = [abs(min(0, delta)) for delta in deltas]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Calculate RSI
        rsi_values = []
        
        for i in range(period, len(deltas)):
            # Update average gain and loss (smoothed)
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            # Calculate RS and RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _calculate_confidence(self, rsi: float, signal_type: str) -> float:
        """Calculate confidence level for the signal."""
        if signal_type == "oversold_recovery":
            # Lower RSI = higher confidence for buy
            if rsi < 20:
                return 0.9
            elif rsi < 25:
                return 0.8
            elif rsi < 30:
                return 0.7
            else:
                return 0.6
        else:  # overbought_reversal
            # Higher RSI = higher confidence for sell
            if rsi > 80:
                return 0.9
            elif rsi > 75:
                return 0.8
            elif rsi > 70:
                return 0.7
            else:
                return 0.6
    
    def __repr__(self):
        return (
            f"<RSIStrategy("
            f"period={self.rsi_period}, "
            f"oversold={self.oversold}, "
            f"overbought={self.overbought})>"
        )
