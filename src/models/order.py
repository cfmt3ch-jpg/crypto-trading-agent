"""
Order Model - Represents a trading order.
"""

from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class Order:
    """Represents a trading order."""
    
    id: str
    pair: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exchange_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_amount: Optional[float] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_active(self) -> bool:
        """Check if order is active."""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed."""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED
        ]
    
    @property
    def total_value(self) -> float:
        """Calculate total order value."""
        return self.amount * self.price
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pair": self.pair,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "amount": self.amount,
            "price": self.price,
            "status": self.status.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exchange_id": self.exchange_id,
            "filled_price": self.filled_price,
            "filled_amount": self.filled_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "error": self.error,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            pair=data["pair"],
            side=OrderSide(data["side"]),
            order_type=OrderType(data["order_type"]),
            amount=float(data["amount"]),
            price=float(data["price"]),
            status=OrderStatus(data["status"]),
            stop_loss=float(data["stop_loss"]) if data.get("stop_loss") else None,
            take_profit=float(data["take_profit"]) if data.get("take_profit") else None,
            exchange_id=data.get("exchange_id"),
            filled_price=float(data["filled_price"]) if data.get("filled_price") else None,
            filled_amount=float(data["filled_amount"]) if data.get("filled_amount") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            filled_at=datetime.fromisoformat(data["filled_at"]) if data.get("filled_at") else None,
            cancelled_at=datetime.fromisoformat(data["cancelled_at"]) if data.get("cancelled_at") else None,
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )
    
    def __repr__(self):
        return (
            f"<Order("
            f"id='{self.id}', "
            f"pair='{self.pair}', "
            f"side={self.side.value}, "
            f"type={self.order_type.value}, "
            f"amount={self.amount}, "
            f"price={self.price}, "
            f"status={self.status.value})>"
        )
