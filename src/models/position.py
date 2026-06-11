"""
Position Model - Represents an open trading position.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    """Represents an open trading position."""
    
    pair: str
    side: str  # "buy" or "sell"
    amount: float
    entry_price: float
    entry_time: datetime
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    final_pnl: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.current_price is None:
            self.current_price = self.entry_price
    
    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.exit_time is None
    
    @property
    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.exit_time is not None
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        if self.side == "buy":
            return (self.current_price - self.entry_price) * self.amount
        else:
            return (self.entry_price - self.current_price) * self.amount
    
    @property
    def unrealized_pnl_percentage(self) -> float:
        """Calculate unrealized PnL as percentage."""
        if self.entry_price == 0:
            return 0.0
        return self.unrealized_pnl / (self.entry_price * self.amount)
    
    @property
    def position_value(self) -> float:
        """Calculate current position value."""
        return self.amount * self.current_price
    
    @property
    def entry_value(self) -> float:
        """Calculate entry value."""
        return self.amount * self.entry_price
    
    def update_pnl(self):
        """Update PnL based on current price."""
        # PnL is automatically calculated via unrealized_pnl property
        pass
    
    def calculate_final_pnl(self):
        """Calculate final PnL when position is closed."""
        if self.exit_price is None:
            self.final_pnl = 0.0
            return
        
        if self.side == "buy":
            self.final_pnl = (self.exit_price - self.entry_price) * self.amount
        else:
            self.final_pnl = (self.entry_price - self.exit_price) * self.amount
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pair": self.pair,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "current_price": self.current_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "final_pnl": self.final_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percentage": self.unrealized_pnl_percentage,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Create from dictionary."""
        return cls(
            pair=data["pair"],
            side=data["side"],
            amount=float(data["amount"]),
            entry_price=float(data["entry_price"]),
            entry_time=datetime.fromisoformat(data["entry_time"]),
            current_price=float(data["current_price"]) if data.get("current_price") else None,
            stop_loss=float(data["stop_loss"]) if data.get("stop_loss") else None,
            take_profit=float(data["take_profit"]) if data.get("take_profit") else None,
            exit_price=float(data["exit_price"]) if data.get("exit_price") else None,
            exit_time=datetime.fromisoformat(data["exit_time"]) if data.get("exit_time") else None,
            final_pnl=float(data.get("final_pnl", 0)),
            metadata=data.get("metadata", {})
        )
    
    def __repr__(self):
        return (
            f"<Position("
            f"pair='{self.pair}', "
            f"side={self.side}, "
            f"amount={self.amount}, "
            f"entry_price={self.entry_price}, "
            f"current_price={self.current_price}, "
            f"pnl={self.unrealized_pnl:.2f})>"
        )
