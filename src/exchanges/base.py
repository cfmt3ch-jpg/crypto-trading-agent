"""
Base Exchange - Abstract base class for exchange implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime

from src.models.candle import Candle


class BaseExchange(ABC):
    """Abstract base class for exchange implementations."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.name = config.get("name", "unknown")
        self.connected = False
    
    @abstractmethod
    async def connect(self):
        """Connect to the exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def get_price(self, pair: str) -> float:
        """Get current price for a pair."""
        pass
    
    @abstractmethod
    async def get_candles(
        self, 
        pair: str, 
        timeframe: str, 
        limit: int = 100
    ) -> List[Candle]:
        """Get candlestick data."""
        pass
    
    @abstractmethod
    async def place_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        amount: float,
        price: float
    ) -> Dict:
        """Place an order on the exchange."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, pair: str) -> Dict:
        """Get order status."""
        pass
    
    @abstractmethod
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"
