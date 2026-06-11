"""
Portfolio Management - Track positions and calculate risk.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from loguru import logger

from src.models.position import Position
from src.exchanges.base import BaseExchange


@dataclass
class PortfolioState:
    """Current state of the portfolio."""
    total_value: float = 0.0
    available_balance: float = 0.0
    open_positions: List[Position] = field(default_factory=list)
    closed_positions: List[Position] = field(default_factory=list)
    initial_value: float = 0.0
    peak_value: float = 0.0


class Portfolio:
    """Manages portfolio state and risk calculations."""
    
    def __init__(self, config: Dict, exchange: BaseExchange):
        self.config = config
        self.exchange = exchange
        self.state = PortfolioState()
        self.risk_config = config.get("risk", {})
    
    async def initialize(self):
        """Initialize portfolio with current balance."""
        logger.info("Initializing portfolio...")
        
        # Get current balance from exchange
        balance = await self.exchange.get_balance()
        
        self.state.available_balance = balance.get("USDT", 0.0)
        self.state.total_value = self.state.available_balance
        self.state.initial_value = self.state.total_value
        self.state.peak_value = self.state.total_value
        
        logger.info(f"Portfolio initialized with {self.state.total_value:.2f} USDT")
    
    async def update(self):
        """Update portfolio state."""
        # Get current prices for open positions
        for position in self.state.open_positions:
            current_price = await self.exchange.get_price(position.pair)
            position.current_price = current_price
            position.update_pnl()
        
        # Calculate total value
        positions_value = sum(
            p.amount * p.current_price 
            for p in self.state.open_positions
        )
        self.state.total_value = self.state.available_balance + positions_value
        
        # Update peak value
        if self.state.total_value > self.state.peak_value:
            self.state.peak_value = self.state.total_value
    
    def can_open_position(self, pair: str) -> bool:
        """Check if we can open a new position."""
        # Check max open trades
        max_trades = self.risk_config.get("max_open_trades", 3)
        if len(self.state.open_positions) >= max_trades:
            return False
        
        # Check if already have position for this pair
        for position in self.state.open_positions:
            if position.pair == pair:
                return False
        
        # Check available balance
        min_trade = self.risk_config.get("min_trade_amount", 10)
        if self.state.available_balance < min_trade:
            return False
        
        return True
    
    def calculate_position_size(
        self, 
        pair: str, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """Calculate position size based on risk management."""
        # Get risk per trade (default 2%)
        risk_per_trade = self.config.get("trading", {}).get("risk_per_trade", 0.02)
        
        # Calculate risk amount
        risk_amount = self.state.total_value * risk_per_trade
        
        # Calculate position size based on stop loss
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            return 0.0
        
        position_size = risk_amount / price_risk
        
        # Limit by available balance
        max_size = self.state.available_balance / entry_price
        position_size = min(position_size, max_size)
        
        # Apply minimum trade amount
        min_trade = self.risk_config.get("min_trade_amount", 10)
        if position_size * entry_price < min_trade:
            return 0.0
        
        return position_size
    
    def add_position(self, position: Position):
        """Add a new position to portfolio."""
        self.state.open_positions.append(position)
        self.state.available_balance -= position.amount * position.entry_price
        logger.info(f"Added position: {position.pair} {position.side}")
    
    def close_position(self, position: Position, exit_price: float):
        """Close a position."""
        position.exit_price = exit_price
        position.exit_time = datetime.now()
        position.calculate_final_pnl()
        
        # Update balance
        self.state.available_balance += position.amount * exit_price
        
        # Move to closed positions
        self.state.open_positions.remove(position)
        self.state.closed_positions.append(position)
        
        logger.info(f"Closed position: {position.pair} PnL: {position.final_pnl:.2f}")
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return self.state.open_positions.copy()
    
    def get_closed_positions(self) -> List[Position]:
        """Get all closed positions."""
        return self.state.closed_positions.copy()
    
    def get_total_value(self) -> float:
        """Get total portfolio value."""
        return self.state.total_value
    
    def get_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if self.state.peak_value == 0:
            return 0.0
        
        drawdown = (self.state.peak_value - self.state.total_value) / self.state.peak_value
        return max(0.0, drawdown)
    
    def get_win_rate(self) -> float:
        """Calculate win rate from closed positions."""
        if not self.state.closed_positions:
            return 0.0
        
        winning_trades = sum(
            1 for p in self.state.closed_positions 
            if p.final_pnl > 0
        )
        
        return winning_trades / len(self.state.closed_positions)
    
    def get_total_pnl(self) -> float:
        """Calculate total profit/loss."""
        return sum(p.final_pnl for p in self.state.closed_positions)
    
    def get_stats(self) -> Dict:
        """Get portfolio statistics."""
        return {
            "total_value": self.state.total_value,
            "available_balance": self.state.available_balance,
            "open_positions": len(self.state.open_positions),
            "closed_positions": len(self.state.closed_positions),
            "drawdown": self.get_drawdown(),
            "win_rate": self.get_win_rate(),
            "total_pnl": self.get_total_pnl(),
            "initial_value": self.state.initial_value
        }
