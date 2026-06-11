"""
Order Management - Handle order creation and execution.
"""

from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from src.models.order import Order, OrderSide, OrderType, OrderStatus
from src.models.position import Position
from src.exchanges.base import BaseExchange
from src.core.portfolio import Portfolio


@dataclass
class OrderResult:
    """Result of an order execution."""
    success: bool
    order: Optional[Order] = None
    error: Optional[str] = None


class OrderManager:
    """Manages order creation and execution."""
    
    def __init__(self, exchange: BaseExchange, portfolio: Portfolio):
        self.exchange = exchange
        self.portfolio = portfolio
        self.pending_orders: Dict[str, Order] = {}
    
    def create_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        amount: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Order:
        """Create a new order."""
        order = Order(
            id=self._generate_order_id(),
            pair=pair,
            side=OrderSide(side),
            order_type=OrderType(order_type),
            amount=amount,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        
        logger.info(f"Created order: {order.side.value} {order.amount} {order.pair} @ {order.price}")
        return order
    
    async def execute_order(self, order: Order) -> OrderResult:
        """Execute an order on the exchange."""
        try:
            # Update order status
            order.status = OrderStatus.SUBMITTED
            
            # Execute on exchange
            result = await self.exchange.place_order(
                pair=order.pair,
                side=order.side.value,
                order_type=order.order_type.value,
                amount=order.amount,
                price=order.price
            )
            
            if result["success"]:
                # Update order with exchange response
                order.exchange_id = result["order_id"]
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
                order.filled_price = result.get("filled_price", order.price)
                
                # Create position
                position = Position(
                    pair=order.pair,
                    side=order.side.value,
                    amount=order.amount,
                    entry_price=order.filled_price,
                    entry_time=order.filled_at,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit
                )
                
                # Add to portfolio
                self.portfolio.add_position(position)
                
                logger.info(f"Order executed: {order.pair} {order.side.value}")
                return OrderResult(success=True, order=order)
            else:
                order.status = OrderStatus.REJECTED
                order.error = result.get("error", "Unknown error")
                logger.warning(f"Order rejected: {order.error}")
                return OrderResult(success=False, error=order.error)
                
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.error = str(e)
            logger.error(f"Order execution failed: {e}")
            return OrderResult(success=False, error=str(e))
    
    async def close_position(self, position: Position) -> OrderResult:
        """Close an open position."""
        try:
            # Get current price
            current_price = await self.exchange.get_price(position.pair)
            
            # Create close order
            close_side = "sell" if position.side == "buy" else "buy"
            
            order = self.create_order(
                pair=position.pair,
                side=close_side,
                order_type="market",
                amount=position.amount,
                price=current_price
            )
            
            # Execute close order
            result = await self.execute_order(order)
            
            if result.success:
                # Update portfolio
                self.portfolio.close_position(position, current_price)
                logger.info(f"Position closed: {position.pair}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return OrderResult(success=False, error=str(e))
    
    async def check_stop_loss(self, position: Position) -> bool:
        """Check if stop loss should be triggered."""
        if not position.stop_loss:
            return False
        
        current_price = await self.exchange.get_price(position.pair)
        
        if position.side == "buy":
            # Long position - trigger if price falls below stop loss
            if current_price <= position.stop_loss:
                logger.info(f"Stop loss triggered for {position.pair}")
                return True
        else:
            # Short position - trigger if price rises above stop loss
            if current_price >= position.stop_loss:
                logger.info(f"Stop loss triggered for {position.pair}")
                return True
        
        return False
    
    async def check_take_profit(self, position: Position) -> bool:
        """Check if take profit should be triggered."""
        if not position.take_profit:
            return False
        
        current_price = await self.exchange.get_price(position.pair)
        
        if position.side == "buy":
            # Long position - trigger if price rises above take profit
            if current_price >= position.take_profit:
                logger.info(f"Take profit triggered for {position.pair}")
                return True
        else:
            # Short position - trigger if price falls below take profit
            if current_price <= position.take_profit:
                logger.info(f"Take profit triggered for {position.pair}")
                return True
        
        return False
    
    def _generate_order_id(self) -> str:
        """Generate a unique order ID."""
        import uuid
        return str(uuid.uuid4())[:8]
