"""
Trade Model - Represents a completed trade (entry + exit).
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Trade:
    """Represents a completed trade."""
    
    id: str
    pair: str
    side: str  # "buy" or "sell"
    amount: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percentage: float
    fees: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    @property
    def duration(self) -> datetime:
        """Calculate trade duration."""
        return self.exit_time - self.entry_time
    
    @property
    def duration_seconds(self) -> float:
        """Calculate trade duration in seconds."""
        return self.duration.total_seconds()
    
    @property
    def is_profitable(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl > 0
    
    @property
    def net_pnl(self) -> float:
        """Calculate net PnL after fees."""
        return self.pnl - self.fees
    
    @property
    def entry_value(self) -> float:
        """Calculate entry value."""
        return self.amount * self.entry_price
    
    @property
    def exit_value(self) -> float:
        """Calculate exit value."""
        return self.amount * self.exit_price
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pair": self.pair,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "fees": self.fees,
            "net_pnl": self.net_pnl,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            pair=data["pair"],
            side=data["side"],
            amount=float(data["amount"]),
            entry_price=float(data["entry_price"]),
            exit_price=float(data["exit_price"]),
            entry_time=datetime.fromisoformat(data["entry_time"]),
            exit_time=datetime.fromisoformat(data["exit_time"]),
            pnl=float(data["pnl"]),
            pnl_percentage=float(data["pnl_percentage"]),
            fees=float(data.get("fees", 0)),
            metadata=data.get("metadata", {})
        )
    
    def __repr__(self):
        return (
            f"<Trade("
            f"id='{self.id}', "
            f"pair='{self.pair}', "
            f"side={self.side}, "
            f"pnl={self.pnl:.2f}, "
            f"pnl%={self.pnl_percentage:.2%})>"
        )
