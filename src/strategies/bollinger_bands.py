"""
Bollinger Bands Strategy - Mean reversion trading strategy.
"""

from typing import Dict, List, Optional
import numpy as np

from src.strategies.base import BaseStrategy, Signal, SignalSide
from src.models.candle import Candle


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands strategy.
    
    Buy when price touches lower band (oversold).
    Sell when price touches upper band (overbought).
    
    Parameters:
    - period: Moving average period (default: 20)
    - std_dev: Standard deviation multiplier (default: 2.0)
    """
    
    def __init__(self, params: Dict):
        super().__init__(params)
        self.period = params.get("period", 20)
        self.std_dev = params.get("std_dev", 2.0)
        self.stop_loss_pct = params.get("stop_loss_pct", 0.05)
        self.take_profit_pct = params.get("take_profit_pct", 0.08)
    
    def generate_signal(self, candles: List[Candle]) -> Optional[Signal]:
        """Generate trading signal based on Bollinger Bands."""
        if len(candles) < self.period + 1:
            return None
        
        # Calculate Bollinger Bands
        closes = [c.close for c in candles]
        upper_band, middle_band, lower_band = self._calculate_bollinger_bands(closes)
        
        if not upper_band or not lower_band:
            return None
        
        # Current values
        current_price = candles[-1].close
        current_upper = upper_band[-1]
        current_middle = middle_band[-1]
        current_lower = lower_band[-1]
        
        # Previous values
        previous_price = candles[-2].close
        previous_lower = lower_band[-2]
        previous_upper = upper_band[-2]
        
        # Calculate bandwidth (volatility indicator)
        bandwidth = (current_upper - current_lower) / current_middle
        
        # Calculate %B (position within bands)
        percent_b = (current_price - current_lower) / (current_upper - current_lower)
        
        # Buy signal: Price bounces off lower band
        if (previous_price <= previous_lower and 
            current_price > current_lower and
            percent_b < 0.3):
            
            return Signal(
                side=SignalSide.BUY,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.BUY, self.stop_loss_pct
                ),
                take_profit=self._calculate_mean_reversion_target(
                    current_price, current_middle, "buy"
                ),
                confidence=self._calculate_confidence(
                    percent_b, bandwidth, "buy"
                ),
                metadata={
                    "upper_band": current_upper,
                    "middle_band": current_middle,
                    "lower_band": current_lower,
                    "bandwidth": bandwidth,
                    "percent_b": percent_b,
                    "signal_type": "lower_band_bounce"
                }
            )
        
        # Sell signal: Price bounces off upper band
        elif (previous_price >= previous_upper and 
              current_price < current_upper and
              percent_b > 0.7):
            
            return Signal(
                side=SignalSide.SELL,
                entry_price=current_price,
                stop_loss=self.calculate_stop_loss(
                    current_price, SignalSide.SELL, self.stop_loss_pct
                ),
                take_profit=self._calculate_mean_reversion_target(
                    current_price, current_middle, "sell"
                ),
                confidence=self._calculate_confidence(
                    percent_b, bandwidth, "sell"
                ),
                metadata={
                    "upper_band": current_upper,
                    "middle_band": current_middle,
                    "lower_band": current_lower,
                    "bandwidth": bandwidth,
                    "percent_b": percent_b,
                    "signal_type": "upper_band_bounce"
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
    
    def _calculate_std_dev(
        self, 
        data: List[float], 
        sma: List[float], 
        period: int
    ) -> List[float]:
        """Calculate Standard Deviation."""
        if len(data) < period or len(sma) < 1:
            return []
        
        std_devs = []
        
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            mean = sma[i - period + 1] if i - period + 1 < len(sma) else sma[-1]
            
            # Calculate variance
            variance = sum((x - mean) ** 2 for x in window) / period
            
            # Standard deviation
            std_devs.append(variance ** 0.5)
        
        return std_devs
    
    def _calculate_bollinger_bands(
        self, 
        data: List[float]
    ) -> tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands (Upper, Middle, Lower)."""
        # Calculate middle band (SMA)
        middle_band = self._calculate_sma(data, self.period)
        
        if not middle_band:
            return [], [], []
        
        # Calculate standard deviation
        std_devs = self._calculate_std_dev(data, middle_band, self.period)
        
        if not std_devs:
            return [], [], []
        
        # Align arrays
        middle_band = middle_band[len(middle_band) - len(std_devs):]
        
        # Calculate upper and lower bands
        upper_band = [
            middle + (self.std_dev * std_dev) 
            for middle, std_dev in zip(middle_band, std_devs)
        ]
        
        lower_band = [
            middle - (self.std_dev * std_dev) 
            for middle, std_dev in zip(middle_band, std_devs)
        ]
        
        return upper_band, middle_band, lower_band
    
    def _calculate_mean_reversion_target(
        self, 
        entry_price: float, 
        middle_band: float,
        side: str
    ) -> float:
        """Calculate take profit target (mean reversion to middle band)."""
        # Target the middle band for mean reversion
        if side == "buy":
            # For buy, target should be above entry
            target = max(middle_band, entry_price * (1 + 0.02))
        else:
            # For sell, target should be below entry
            target = min(middle_band, entry_price * (1 - 0.02))
        
        return target
    
    def _calculate_confidence(
        self, 
        percent_b: float, 
        bandwidth: float,
        side: str
    ) -> float:
        """Calculate confidence level for the signal."""
        # Base confidence
        confidence = 0.6
        
        # Stronger signal if price is at extreme
        if side == "buy":
            # Lower %B = more oversold = higher confidence
            if percent_b < 0.1:
                confidence += 0.2
            elif percent_b < 0.2:
                confidence += 0.1
        else:
            # Higher %B = more overbought = higher confidence
            if percent_b > 0.9:
                confidence += 0.2
            elif percent_b > 0.8:
                confidence += 0.1
        
        # Adjust based on volatility (bandwidth)
        # Higher volatility = potentially larger moves
        if bandwidth > 0.05:  # 5% bandwidth
            confidence += 0.05
        
        return min(0.9, max(0.5, confidence))
    
    def __repr__(self):
        return (
            f"<BollingerBandsStrategy("
            f"period={self.period}, "
            f"std_dev={self.std_dev})>"
        )
