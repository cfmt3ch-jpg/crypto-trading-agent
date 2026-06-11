"""
Binance Exchange Implementation
"""

import ccxt.async_support as ccxt
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger

from src.exchanges.base import BaseExchange
from src.models.candle import Candle


class BinanceExchange(BaseExchange):
    """Binance exchange implementation using CCXT."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.exchange: Optional[ccxt.binance] = None
    
    async def connect(self):
        """Connect to Binance."""
        try:
            self.exchange = ccxt.binance({
                "apiKey": self.config.get("api_key"),
                "secret": self.config.get("api_secret"),
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True
                }
            })
            
            # Set testnet if configured
            if self.config.get("testnet", False):
                self.exchange.set_sandbox_mode(True)
                logger.info("Connected to Binance Testnet")
            else:
                logger.info("Connected to Binance")
            
            # Load markets
            await self.exchange.load_markets()
            self.connected = True
            
            logger.info(f"Loaded {len(self.exchange.markets)} markets")
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Binance."""
        if self.exchange:
            await self.exchange.close()
            self.connected = False
            logger.info("Disconnected from Binance")
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        try:
            balance = await self.exchange.fetch_balance()
            return {
                currency: float(info["free"])
                for currency, info in balance.items()
                if isinstance(info, dict) and "free" in info
            }
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}
    
    async def get_price(self, pair: str) -> float:
        """Get current price for a pair."""
        try:
            ticker = await self.exchange.fetch_ticker(pair)
            return float(ticker["last"])
        except Exception as e:
            logger.error(f"Error fetching price for {pair}: {e}")
            return 0.0
    
    async def get_candles(
        self, 
        pair: str, 
        timeframe: str, 
        limit: int = 100
    ) -> List[Candle]:
        """Get candlestick data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=pair,
                timeframe=timeframe,
                limit=limit
            )
            
            candles = []
            for data in ohlcv:
                candle = Candle(
                    timestamp=datetime.fromtimestamp(data[0] / 1000),
                    open=float(data[1]),
                    high=float(data[2]),
                    low=float(data[3]),
                    close=float(data[4]),
                    volume=float(data[5])
                )
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching candles for {pair}: {e}")
            return []
    
    async def place_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        amount: float,
        price: float
    ) -> Dict:
        """Place an order on Binance."""
        try:
            # Create order
            order = await self.exchange.create_order(
                symbol=pair,
                type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            
            logger.info(f"Order placed: {order['id']}")
            
            return {
                "success": True,
                "order_id": order["id"],
                "filled_price": float(order.get("price", price)),
                "filled_amount": float(order.get("filled", amount))
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an order."""
        try:
            await self.exchange.cancel_order(order_id, pair)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order(self, order_id: str, pair: str) -> Dict:
        """Get order status."""
        try:
            order = await self.exchange.fetch_order(order_id, pair)
            return {
                "id": order["id"],
                "status": order["status"],
                "filled": float(order.get("filled", 0)),
                "remaining": float(order.get("remaining", 0)),
                "price": float(order.get("price", 0)),
                "average": float(order.get("average", 0))
            }
        except Exception as e:
            logger.error(f"Error fetching order: {e}")
            return {}
    
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        try:
            orders = await self.exchange.fetch_open_orders(pair)
            return [
                {
                    "id": order["id"],
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "type": order["type"],
                    "price": float(order.get("price", 0)),
                    "amount": float(order.get("amount", 0)),
                    "filled": float(order.get("filled", 0))
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
