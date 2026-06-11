"""
MACD Strategy - Moving Average Convergence Divergence trading strategy.
"""

from typing import Dict, List, Optional

from src.strategies.base import BaseStrategy, Signal, SignalSide
from src.models.candle import Candle


class MACDStrategy(BaseStrategy):
    """MACD (Moving Average Convergence Divergence) strategy.
    
    Buy when MACD line crosses above signal line.
    Sell when MACD line crosses below signal line.
    
    Parameters:
    - fast_period: Fast EMA period (default: 12)
    - slow_period: Slow EMA period (default: 26)
    - signal_period: Signal line period (default: 9)
    """
    
    def __init__(self, params: Dict):
        super().__init__(params)
        self.fast_period = params.get("fast_period", 12)
        self.slow_period = params.get("slow_period", 26)
        self.signal_period = params.get("signal_period", 9)
        self.stop_loss_pct = params.get("stop_loss_pct", 0.05)
        self.take_profit_pct = params.get("take_profit_pct", 0.10)
    
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        """Generate trading signal based on MACD crossover."""
        if len(candles) < self.slow_period + self.signal_period:
            return None
        
        # Calculate MACD
        closes = [c.close for c in candles]
        macd_line, signal_line, histogram = self._calculate_macd(closes)
        
        if len(macd_line) < 2 or len(signal_line) < 2:
            return None
        
        # Current values
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        previous_macd = macd_line[-2]
        previous_signal = signal_line[-2]
        
        # Current price
        current_price = candles[-1].close
        
        # Bullish crossover: MACD crosses above signal
        if previous_macd <= previous_signal and current_macd > current_signal:
            # Check if histogram is positive (momentum confirmation)
            if histogram[-1] > 0:
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
                        macd_line, signal_line, histogram, "bullish"
                    ),
                    metadata={
                        "macd": current_macd,
                        "signal": current_signal,
                        "histogram": histogram[-1],
                        "crossover_type": "bullish"
                    }
                )
        
        # Bearish crossover: MACD crosses below signal
        elif previous_macd >= previous_signal and current_macd < current_signal:
            # Check if histogram is negative (momentum confirmation)
            if histogram[-1] < 0:
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
                        macd_line, signal_line, histogram, "bearish"
                    ),
                    metadata={
                        "macd": current_macd,
                        "signal": current_signal,
                        "histogram": histogram[-1],
                        "crossover_type": "bearish"
                    }
                )
        
        # No signal
        return None
    
    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return []
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate initial SMA
        sma = sum(data[:period]) / period
        ema = [sma]
        
        # Calculate EMA
        for i in range(period, len(data)):
            value = (data[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(value)
        
        return ema
    
    def _calculate_macd(
        self, 
        data: List[float]
    ) -> tuple[List[float], List[float], List[float]]:
        """Calculate MACD line, signal line, and histogram."""
        # Calculate EMAs
        fast_ema = self._calculate_ema(data, self.fast_period)
        slow_ema = self._calculate_ema(data, self.slow_period)
        
        # Align EMAs (slow EMA is shorter)
        fast_ema = fast_ema[len(fast_ema) - len(slow_ema):]
        
        # Calculate MACD line
        macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]
        
        # Calculate signal line (EMA of MACD)
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Align MACD line
        macd_line = macd_line[len(macd_line) - len(signal_line):]
        
        # Calculate histogram
        histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]
        
        return macd_line, signal_line, histogram
    
    def _calculate_confidence(
        self, 
        macd_line: List[float], 
        signal_line: List[float],
        histogram: List[float],
        crossover_type: str
    ) -> float:
        """Calculate confidence level for the signal."""
        if not histogram:
            return 0.5
        
        # Base confidence
        confidence = 0.6
        
        # Stronger signal if histogram is growing
        if len(histogram) >= 2:
            if crossover_type == "bullish" and histogram[-1] > histogram[-2]:
                confidence += 0.1
            elif crossover_type == "bearish" and histogram[-1] < histogram[-2]:
                confidence += 0.1
        
        # Stronger signal if MACD is far from zero
        if abs(macd_line[-1]) > abs(signal_line[-1]) * 0.5:
            confidence += 0.1
        
        return min(0.9, max(0.5, confidence))
    
    def __repr__(self):
        return (
            f"<MACDStrategy("
            f"fast={self.fast_period}, "
            f"slow={self.slow_period}, "
            f"signal={self.signal_period})>"
        )
