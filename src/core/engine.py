"""
Core Trading Engine - Main orchestrator for the trading agent.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.core.portfolio import Portfolio
from src.core.order_manager import OrderManager
from src.strategies.base import BaseStrategy, SignalSide
from src.strategies import get_strategy
from src.exchanges.base import BaseExchange
from src.exchanges.binance import BinanceExchange
from src.exchanges.paper_trading import PaperTradingExchange
from src.models.candle import Candle
from src.models.trade import Trade


class TradingEngine:
    """Main trading engine that orchestrates all components."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        self.exchange: Optional[BaseExchange] = None
        self.strategy: Optional[BaseStrategy] = None
        self.portfolio: Optional[Portfolio] = None
        self.order_manager: Optional[OrderManager] = None
        
        # Real price feed (Hyperliquid)
        self._price_feed = None
        
        # Statistics
        self.stats = {
            "start_time": None,
            "trades_executed": 0,
            "total_profit_loss": 0.0,
            "win_rate": 0.0
        }
    
    async def start(self):
        """Start the trading engine."""
        logger.info("Initializing trading engine...")
        
        # Initialize exchange
        self.exchange = self._init_exchange()
        await self.exchange.connect()
        
        # Initialize real price feed for paper trading
        if self.config["exchange"]["name"] == "paper_trading":
            await self._init_real_price_feed()
        
        # Initialize portfolio
        self.portfolio = Portfolio(self.config, self.exchange)
        await self.portfolio.initialize()
        
        # Initialize order manager
        self.order_manager = OrderManager(self.exchange, self.portfolio)
        
        # Initialize strategy
        self.strategy = self._init_strategy()
        
        # Mark as running
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        logger.info("Trading engine started successfully!")
        logger.info(f"Trading pairs: {self.config['trading']['pairs']}")
        logger.info(f"Strategy: {self.config['strategy']['name']}")
        logger.info(f"Exchange: {self.config['exchange']['name']}")
        
        # Main trading loop
        await self._trading_loop()
    
    def stop(self):
        """Stop the trading engine."""
        logger.info("Stopping trading engine...")
        self.running = False
        
        # Close all positions if configured
        if self.config.get("trading", {}).get("close_on_stop", False):
            asyncio.create_task(self._close_all_positions())
        
        # Disconnect from exchange
        if self.exchange:
            asyncio.create_task(self.exchange.disconnect())
        
        logger.info("Trading engine stopped.")
    
    async def _init_real_price_feed(self):
        """Initialize real price feed from Hyperliquid."""
        try:
            from src.exchanges.hyperliquid import HyperliquidExchange
            
            # Create Hyperliquid connection for price feed only
            hl_config = {
                "name": "hyperliquid",
                "testnet": False,
                "account_address": "",
                "private_key": ""
            }
            
            self._price_feed = HyperliquidExchange(hl_config)
            await self._price_feed.connect()
            
            logger.info("Real price feed initialized (Hyperliquid)")
            
        except Exception as e:
            logger.warning(f"Could not initialize real price feed: {e}")
            logger.info("Using simulated prices")
    
    async def _trading_loop(self):
        """Main trading loop."""
        logger.info("Starting trading loop...")
        
        while self.running:
            try:
                # Get current time
                now = datetime.now()
                
                # Update prices from real feed
                if self._price_feed:
                    await self._update_real_prices()
                
                # Check if it's time to trade (based on timeframe)
                if self._should_trade(now):
                    await self._execute_trading_cycle()
                
                # Sleep for a short interval
                await asyncio.sleep(1)  # 1 second
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _update_real_prices(self):
        """Update prices from real price feed."""
        try:
            for pair in self.config["trading"]["pairs"]:
                price = await self._price_feed.get_price(pair)
                if price > 0:
                    self.exchange.set_price(pair, price)
        except Exception as e:
            logger.debug(f"Error updating prices: {e}")
    
    def _should_trade(self, now: datetime) -> bool:
        """Check if it's time to execute a trading cycle."""
        # For now, always trade (will be refined based on timeframe)
        return True
    
    async def _execute_trading_cycle(self):
        """Execute one trading cycle."""
        try:
            # Get current market data
            for pair in self.config["trading"]["pairs"]:
                # Fetch candles
                candles = await self.exchange.get_candles(
                    pair,
                    self.config["trading"]["timeframe"],
                    limit=100
                )
                
                if not candles:
                    continue
                
                # Generate trading signal
                signal = self.strategy.generate_signal(candles)
                
                # Execute signal if valid
                if signal and signal.is_valid():
                    await self._execute_signal(pair, signal)
            
            # Update portfolio
            await self.portfolio.update()
            
            # Check risk management
            await self._check_risk_management()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    async def _execute_signal(self, pair: str, signal):
        """Execute a trading signal."""
        try:
            # Check if we can open a new position
            if not self.portfolio.can_open_position(pair):
                logger.debug(f"Cannot open position for {pair}")
                return
            
            # Calculate position size
            position_size = self.portfolio.calculate_position_size(
                pair,
                signal.entry_price,
                signal.stop_loss
            )
            
            if position_size <= 0:
                logger.debug(f"Position size too small for {pair}")
                return
            
            # Convert SignalSide to string
            side_str = signal.side.value if isinstance(signal.side, SignalSide) else signal.side
            
            # Create order
            order = self.order_manager.create_order(
                pair=pair,
                side=side_str,
                order_type=self.config["orders"]["default_type"],
                amount=position_size,
                price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            # Execute order
            result = await self.order_manager.execute_order(order)
            
            if result.success:
                logger.info(f"Order executed: {side_str} {position_size:.6f} {pair} @ {signal.entry_price:.2f}")
                self.stats["trades_executed"] += 1
            else:
                logger.warning(f"Order failed: {result.error}")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _check_risk_management(self):
        """Check risk management rules."""
        # Check max drawdown
        drawdown = self.portfolio.get_drawdown()
        max_drawdown = self.config.get("risk", {}).get("max_drawdown", 0.20)
        
        if drawdown > max_drawdown:
            logger.warning(f"Max drawdown exceeded: {drawdown:.2%} > {max_drawdown:.2%}")
            await self._close_all_positions()
            self.stop()
    
    async def _close_all_positions(self):
        """Close all open positions."""
        logger.info("Closing all positions...")
        positions = self.portfolio.get_open_positions()
        
        for position in positions:
            try:
                await self.order_manager.close_position(position)
                logger.info(f"Closed position: {position.pair}")
            except Exception as e:
                logger.error(f"Error closing position {position.pair}: {e}")
    
    def _init_exchange(self) -> BaseExchange:
        """Initialize the exchange connection."""
        exchange_name = self.config["exchange"]["name"]
        
        if exchange_name == "binance":
            return BinanceExchange(self.config["exchange"])
        elif exchange_name == "paper_trading":
            return PaperTradingExchange(self.config["exchange"])
        elif exchange_name == "hyperliquid":
            from src.exchanges.hyperliquid import HyperliquidExchange
            return HyperliquidExchange(self.config["exchange"])
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    def _init_strategy(self) -> BaseStrategy:
        """Initialize the trading strategy."""
        strategy_name = self.config["strategy"]["name"]
        strategy_params = self.config["strategy"]["params"]
        
        return get_strategy(strategy_name, strategy_params)
    
    def get_stats(self) -> Dict:
        """Get trading statistics."""
        return {
            **self.stats,
            "uptime": str(datetime.now() - self.stats["start_time"]) if self.stats["start_time"] else "0:00:00",
            "portfolio_value": self.portfolio.get_total_value() if self.portfolio else 0.0,
            "open_positions": len(self.portfolio.get_open_positions()) if self.portfolio else 0
        }
