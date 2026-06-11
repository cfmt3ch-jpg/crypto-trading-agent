"""
Paper Trading Exchange - Simulated exchange for testing strategies.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from loguru import logger

from src.exchanges.base import BaseExchange
from src.models.candle import Candle


class PaperTradingExchange(BaseExchange):
    """Simulated exchange for paper trading and backtesting."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "paper_trading"
        
        # Initial balance
        self.initial_balance = config.get("initial_balance", 10000.0)
        self.balance = {"USDT": self.initial_balance}
        
        # Order book simulation
        self.open_orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []
        
        # Position tracking
        self.positions: Dict[str, Dict] = {}
        
        # Fee configuration
        self.maker_fee = config.get("maker_fee", 0.001)  # 0.1%
        self.taker_fee = config.get("taker_fee", 0.001)  # 0.1%
        
        # Slippage simulation
        self.slippage = config.get("slippage", 0.0005)  # 0.05%
        
        # Price feed (set externally)
        self._current_prices: Dict[str, float] = {}
        
        # Statistics
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "peak_balance": self.initial_balance
        }
    
    async def connect(self):
        """Connect to paper trading (no actual connection needed)."""
        self.connected = True
        logger.info(f"Paper Trading initialized with {self.initial_balance} USDT")
    
    async def disconnect(self):
        """Disconnect from paper trading."""
        self.connected = False
        logger.info("Paper Trading disconnected")
    
    def set_price(self, pair: str, price: float):
        """Set current price for a pair (for simulation)."""
        self._current_prices[pair] = price
    
    def set_prices(self, prices: Dict[str, float]):
        """Set multiple prices at once."""
        self._current_prices.update(prices)
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        return self.balance.copy()
    
    async def get_price(self, pair: str) -> float:
        """Get current price for a pair."""
        if pair in self._current_prices:
            return self._current_prices[pair]
        
        # Generate mock price if not set
        mock_prices = {
            "BTC/USDT": 50000.0,
            "ETH/USDT": 3000.0,
            "SOL/USDT": 100.0,
            "BTC/USDC": 50000.0,
            "ETH/USDC": 3000.0
        }
        
        return mock_prices.get(pair, 100.0)
    
    async def get_candles(
        self, 
        pair: str, 
        timeframe: str, 
        limit: int = 100
    ) -> List[Candle]:
        """Get candlestick data (simulated)."""
        # Generate simulated candles
        candles = []
        base_price = await self.get_price(pair)
        
        import random
        
        current_time = datetime.now()
        price = base_price
        
        for i in range(limit):
            # Random price movement
            change_pct = random.uniform(-0.02, 0.02)  # ±2%
            price = price * (1 + change_pct)
            
            # Generate OHLCV
            open_price = price
            high_price = price * (1 + random.uniform(0, 0.01))
            low_price = price * (1 - random.uniform(0, 0.01))
            close_price = price * (1 + random.uniform(-0.005, 0.005))
            volume = random.uniform(1000, 10000)
            
            candle = Candle(
                timestamp=current_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            )
            candles.append(candle)
            
            # Move time backwards
            from datetime import timedelta
            timeframe_deltas = {
                "1m": timedelta(minutes=1),
                "5m": timedelta(minutes=5),
                "15m": timedelta(minutes=15),
                "1h": timedelta(hours=1),
                "4h": timedelta(hours=4),
                "1d": timedelta(days=1)
            }
            current_time -= timeframe_deltas.get(timeframe, timedelta(hours=1))
        
        return list(reversed(candles))
    
    async def place_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        amount: float,
        price: float
    ) -> Dict:
        """Place an order on paper trading."""
        try:
            order_id = str(uuid.uuid4())[:8]
            
            # Apply slippage
            if order_type == "market":
                slippage_factor = 1 + self.slippage if side == "buy" else 1 - self.slippage
                execution_price = price * slippage_factor
            else:
                execution_price = price
            
            # Calculate fees
            fee_rate = self.taker_fee if order_type == "market" else self.maker_fee
            fee = amount * execution_price * fee_rate
            
            # Check balance
            if side == "buy":
                required = amount * execution_price + fee
                if self.balance.get("USDT", 0) < required:
                    return {
                        "success": False,
                        "error": f"Insufficient balance. Required: {required:.2f} USDT"
                    }
                
                # Deduct balance
                self.balance["USDT"] -= required
                
                # Add position
                if pair in self.positions:
                    # Average up/down
                    pos = self.positions[pair]
                    total_cost = pos["size"] * pos["avg_price"] + amount * execution_price
                    pos["size"] += amount
                    pos["avg_price"] = total_cost / pos["size"]
                else:
                    self.positions[pair] = {
                        "side": "long",
                        "size": amount,
                        "avg_price": execution_price,
                        "entry_time": datetime.now()
                    }
            
            else:  # sell
                if pair not in self.positions:
                    return {
                        "success": False,
                        "error": f"No position to sell for {pair}"
                    }
                
                pos = self.positions[pair]
                if pos["size"] < amount:
                    return {
                        "success": False,
                        "error": f"Insufficient position size. Available: {pos['size']}"
                    }
                
                # Calculate PnL
                pnl = (execution_price - pos["avg_price"]) * amount
                
                # Update balance
                self.balance["USDT"] += amount * execution_price - fee + pnl
                
                # Update position
                pos["size"] -= amount
                if pos["size"] <= 0:
                    del self.positions[pair]
                
                # Update stats
                self.stats["total_trades"] += 1
                self.stats["total_pnl"] += pnl
                if pnl > 0:
                    self.stats["winning_trades"] += 1
                else:
                    self.stats["losing_trades"] += 1
            
            # Create order record
            order = {
                "id": order_id,
                "pair": pair,
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": execution_price,
                "fee": fee,
                "timestamp": datetime.now(),
                "status": "filled"
            }
            
            self.order_history.append(order)
            
            # Update peak balance and drawdown
            total_value = self._calculate_total_value()
            if total_value > self.stats["peak_balance"]:
                self.stats["peak_balance"] = total_value
            drawdown = (self.stats["peak_balance"] - total_value) / self.stats["peak_balance"]
            self.stats["max_drawdown"] = max(self.stats["max_drawdown"], drawdown)
            
            logger.info(
                f"Paper trade: {side} {amount} {pair} @ {execution_price:.2f} "
                f"(fee: {fee:.2f})"
            )
            
            return {
                "success": True,
                "order_id": order_id,
                "filled_price": execution_price,
                "filled_amount": amount,
                "fee": fee
            }
            
        except Exception as e:
            logger.error(f"Paper trading error: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an order (not applicable for paper trading)."""
        return True
    
    async def get_order(self, order_id: str, pair: str) -> Dict:
        """Get order status."""
        for order in self.order_history:
            if order["id"] == order_id:
                return order
        return {}
    
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        return []
    
    def get_positions(self) -> Dict[str, Dict]:
        """Get current positions."""
        return self.positions.copy()
    
    def _calculate_total_value(self) -> float:
        """Calculate total portfolio value."""
        total = self.balance.get("USDT", 0)
        
        for pair, pos in self.positions.items():
            price = self._current_prices.get(pair, pos["avg_price"])
            total += pos["size"] * price
        
        return total
    
    def get_stats(self) -> Dict:
        """Get trading statistics."""
        total_value = self._calculate_total_value()
        
        return {
            **self.stats,
            "initial_balance": self.initial_balance,
            "current_balance": self.balance.get("USDT", 0),
            "total_value": total_value,
            "total_return": (total_value - self.initial_balance) / self.initial_balance,
            "win_rate": (
                self.stats["winning_trades"] / self.stats["total_trades"] 
                if self.stats["total_trades"] > 0 else 0
            ),
            "positions": len(self.positions),
            "order_count": len(self.order_history)
        }
    
    def reset(self):
        """Reset paper trading state."""
        self.balance = {"USDT": self.initial_balance}
        self.positions.clear()
        self.order_history.clear()
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "peak_balance": self.initial_balance
        }
        logger.info("Paper trading reset")
    
    def __repr__(self):
        return (
            f"<PaperTradingExchange("
            f"balance={self.balance.get('USDT', 0):.2f} USDT, "
            f"positions={len(self.positions)})>"
        )
