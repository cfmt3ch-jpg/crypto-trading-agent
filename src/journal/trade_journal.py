"""
Trade Journal - Records all trades with detailed information.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class JournalEntry:
    """A single trade journal entry."""
    
    id: str
    timestamp: str
    pair: str
    side: str  # buy/sell
    action: str  # open/close
    amount: float
    price: float
    total_value: float
    
    # Strategy info
    strategy: str
    signal_type: str  # e.g., "bullish_crossover", "oversold_recovery"
    confidence: float
    
    # Market conditions
    market_trend: str  # bullish/bearish/sideways
    volatility: str  # low/medium/high
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Result (for closed trades)
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    duration_seconds: Optional[int] = None
    
    # Reason
    entry_reason: str = ""
    exit_reason: str = ""
    
    # Additional notes
    notes: str = ""
    emotions: str = ""  # confident, fearful, greedy, etc.
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class TradeJournal:
    """Manages trade journal entries."""
    
    def __init__(self, journal_path: str = "data/journal"):
        self.journal_path = Path(journal_path)
        self.journal_path.mkdir(parents=True, exist_ok=True)
        self.entries: List[JournalEntry] = []
        self._load_entries()
    
    def _load_entries(self):
        """Load journal entries from file."""
        journal_file = self.journal_path / "journal.json"
        if journal_file.exists():
            try:
                with open(journal_file, "r") as f:
                    data = json.load(f)
                    self.entries = [JournalEntry(**entry) for entry in data]
            except Exception as e:
                print(f"Error loading journal: {e}")
                self.entries = []
    
    def _save_entries(self):
        """Save journal entries to file."""
        journal_file = self.journal_path / "journal.json"
        try:
            with open(journal_file, "w") as f:
                json.dump([asdict(e) for e in self.entries], f, indent=2)
        except Exception as e:
            print(f"Error saving journal: {e}")
    
    def add_entry(self, entry: JournalEntry):
        """Add a new journal entry."""
        self.entries.append(entry)
        self._save_entries()
    
    def record_trade_open(
        self,
        trade_id: str,
        pair: str,
        side: str,
        amount: float,
        price: float,
        strategy: str,
        signal_type: str,
        confidence: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        entry_reason: str = "",
        market_trend: str = "unknown",
        volatility: str = "medium",
        notes: str = "",
        tags: List[str] = None
    ) -> JournalEntry:
        """Record a trade opening."""
        
        # Calculate risk/reward ratio
        risk_reward = None
        if stop_loss and take_profit:
            risk = abs(price - stop_loss)
            reward = abs(take_profit - price)
            if risk > 0:
                risk_reward = reward / risk
        
        entry = JournalEntry(
            id=trade_id,
            timestamp=datetime.now().isoformat(),
            pair=pair,
            side=side,
            action="open",
            amount=amount,
            price=price,
            total_value=amount * price,
            strategy=strategy,
            signal_type=signal_type,
            confidence=confidence,
            market_trend=market_trend,
            volatility=volatility,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward,
            entry_reason=entry_reason,
            notes=notes,
            tags=tags or []
        )
        
        self.add_entry(entry)
        return entry
    
    def record_trade_close(
        self,
        trade_id: str,
        pair: str,
        side: str,
        amount: float,
        exit_price: float,
        entry_price: float,
        pnl: float,
        pnl_percentage: float,
        duration_seconds: int,
        exit_reason: str = "",
        emotions: str = "",
        notes: str = "",
        tags: List[str] = None
    ) -> JournalEntry:
        """Record a trade closing."""
        
        entry = JournalEntry(
            id=f"{trade_id}_close",
            timestamp=datetime.now().isoformat(),
            pair=pair,
            side=side,
            action="close",
            amount=amount,
            price=exit_price,
            total_value=amount * exit_price,
            strategy="",
            signal_type="",
            confidence=0,
            market_trend="",
            volatility="",
            exit_price=exit_price,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            duration_seconds=duration_seconds,
            exit_reason=exit_reason,
            emotions=emotions,
            notes=notes,
            tags=tags or []
        )
        
        self.add_entry(entry)
        return entry
    
    def get_entries(
        self,
        pair: Optional[str] = None,
        action: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 50
    ) -> List[JournalEntry]:
        """Get journal entries with optional filters."""
        entries = self.entries.copy()
        
        if pair:
            entries = [e for e in entries if e.pair == pair]
        
        if action:
            entries = [e for e in entries if e.action == action]
        
        if strategy:
            entries = [e for e in entries if e.strategy == strategy]
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries[:limit]
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get complete trade history (open + close paired)."""
        trades = {}
        
        for entry in self.entries:
            if entry.action == "open":
                trade_id = entry.id
                if trade_id not in trades:
                    trades[trade_id] = {
                        "id": trade_id,
                        "open": entry,
                        "close": None
                    }
            elif entry.action == "close":
                # Find the matching open trade
                original_id = entry.id.replace("_close", "")
                if original_id in trades:
                    trades[original_id]["close"] = entry
        
        # Convert to list and sort
        trade_list = list(trades.values())
        trade_list.sort(
            key=lambda t: t["open"].timestamp if t["open"] else "",
            reverse=True
        )
        
        return trade_list[:limit]
    
    def get_statistics(self) -> Dict:
        """Get journal statistics."""
        total_trades = len([e for e in self.entries if e.action == "open"])
        closed_trades = len([e for e in self.entries if e.action == "close"])
        
        # Calculate PnL stats
        pnls = [e.pnl for e in self.entries if e.pnl is not None]
        winning_trades = len([p for p in pnls if p > 0])
        losing_trades = len([p for p in pnls if p < 0])
        
        total_pnl = sum(pnls) if pnls else 0
        avg_pnl = total_pnl / len(pnls) if pnls else 0
        
        win_rate = winning_trades / closed_trades if closed_trades > 0 else 0
        
        # Strategy breakdown
        strategies = {}
        for entry in self.entries:
            if entry.strategy and entry.action == "open":
                if entry.strategy not in strategies:
                    strategies[entry.strategy] = 0
                strategies[entry.strategy] += 1
        
        return {
            "total_trades": total_trades,
            "closed_trades": closed_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "strategies": strategies
        }
    
    def export_to_csv(self, filepath: str):
        """Export journal to CSV."""
        import csv
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "ID", "Timestamp", "Pair", "Side", "Action",
                "Amount", "Price", "Total Value", "Strategy",
                "Signal Type", "Confidence", "Stop Loss", "Take Profit",
                "PnL", "PnL %", "Duration", "Entry Reason", "Exit Reason",
                "Notes", "Emotions", "Tags"
            ])
            
            # Data
            for entry in self.entries:
                writer.writerow([
                    entry.id, entry.timestamp, entry.pair, entry.side,
                    entry.action, entry.amount, entry.price, entry.total_value,
                    entry.strategy, entry.signal_type, entry.confidence,
                    entry.stop_loss, entry.take_profit, entry.pnl,
                    entry.pnl_percentage, entry.duration_seconds,
                    entry.entry_reason, entry.exit_reason, entry.notes,
                    entry.emotions, ", ".join(entry.tags)
                ])
    
    def clear(self):
        """Clear all journal entries."""
        self.entries = []
        self._save_entries()
