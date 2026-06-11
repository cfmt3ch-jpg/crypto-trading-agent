"""
Hyperliquid Exchange Implementation
Hyperliquid is a decentralized perpetual exchange with CEX-like experience.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger

from src.exchanges.base import BaseExchange
from src.models.candle import Candle

try:
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange
    from hyperliquid.utils import constants
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    logger.warning("Hyperliquid SDK not installed. Install with: pip install hyperliquid-python-sdk")


class HyperliquidExchange(BaseExchange):
    """Hyperliquid DEX exchange implementation."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "hyperliquid"
        self.info: Optional['Info'] = None
        self.exchange: Optional['Exchange'] = None
        self.wallet_address = config.get("wallet_address")
        self.private_key = config.get("private_key")
        self.testnet = config.get("testnet", True)
        
        # Hyperliquid uses USDC as base currency
        self.base_currency = "USDC"
        
        # Market info cache
        self._markets = {}
        self._market_cache_time = None
    
    async def connect(self):
        """Connect to Hyperliquid."""
        if not HYPERLIQUID_AVAILABLE:
            raise ImportError("Hyperliquid SDK not installed")
        
        try:
            # Set API URL based on testnet/mainnet
            if self.testnet:
                api_url = constants.TESTNET_API_URL
                logger.info("Connecting to Hyperliquid Testnet...")
            else:
                api_url = constants.MAINNET_API_URL
                logger.info("Connecting to Hyperliquid Mainnet...")
            
            # Initialize Info client (read-only)
            self.info = Info(api_url, skip_ws=True)
            
            # Initialize Exchange client (trading)
            if self.private_key:
                self.exchange = Exchange(
                    private_key=self.private_key,
                    base_url=api_url
                )
                logger.info("Exchange client initialized with trading capabilities")
            else:
                logger.warning("No private key provided. Trading disabled.")
            
            # Load markets
            await self._load_markets()
            
            self.connected = True
            logger.info(f"Connected to Hyperliquid ({len(self._markets)} markets)")
            
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Hyperliquid."""
        self.info = None
        self.exchange = None
        self.connected = False
        logger.info("Disconnected from Hyperliquid")
    
    async def _load_markets(self):
        """Load market information."""
        try:
            # Get meta info (all markets)
            meta = self.info.meta()
            
            if meta and "universe" in meta:
                for market in meta["universe"]:
                    symbol = market["name"]
                    self._markets[symbol] = {
                        "symbol": symbol,
                        "sz_decimals": market.get("szDecimals", 0),
                        "max_leverage": market.get("maxLeverage", 1),
                        "margin_table_id": market.get("marginTableId"),
                        "is_delisted": market.get("isDelisted", False)
                    }
            
            self._market_cache_time = datetime.now()
            logger.info(f"Loaded {len(self._markets)} markets from Hyperliquid")
            
        except Exception as e:
            logger.error(f"Error loading markets: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        try:
            if not self.wallet_address:
                return {self.base_currency: 0.0}
            
            # Get user state
            user_state = self.info.user_state(self.wallet_address)
            
            balance = {}
            
            # Extract USDC balance
            if "marginSummary" in user_state:
                margin = user_state["marginSummary"]
                balance[self.base_currency] = float(margin.get("accountValue", 0))
            
            # Extract per-asset balances
            if "assetPositions" in user_state:
                for pos in user_state["assetPositions"]:
                    if "position" in pos:
                        position = pos["position"]
                        coin = position.get("coin", "")
                        size = float(position.get("szi", 0))
                        if size != 0:
                            balance[coin] = abs(size)
            
            return balance
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {self.base_currency: 0.0}
    
    async def get_price(self, pair: str) -> float:
        """Get current price for a pair."""
        try:
            # Convert pair format (BTC/USDC -> BTC)
            coin = self._normalize_symbol(pair)
            
            # Get all mid prices
            all_mids = self.info.all_mids()
            
            if coin in all_mids:
                return float(all_mids[coin])
            else:
                logger.warning(f"Price not found for {coin}")
                return 0.0
                
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
            coin = self._normalize_symbol(pair)
            
            # Convert timeframe to Hyperliquid format
            interval = self._convert_timeframe(timeframe)
            
            # Calculate lookback based on timeframe and limit
            lookback_hours = self._calculate_lookback(timeframe, limit)
            
            # Get candles
            candles_data = self.info.candles_snapshot(
                coin=coin,
                interval=interval,
                lookback_hours=lookback_hours
            )
            
            candles = []
            for data in candles_data[-limit:]:
                candle = Candle(
                    timestamp=datetime.fromtimestamp(data["t"] / 1000),
                    open=float(data["o"]),
                    high=float(data["h"]),
                    low=float(data["l"]),
                    close=float(data["c"]),
                    volume=float(data["v"])
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
        """Place an order on Hyperliquid."""
        try:
            if not self.exchange:
                return {"success": False, "error": "Trading not enabled (no private key)"}
            
            coin = self._normalize_symbol(pair)
            
            # Determine if buy or sell
            is_buy = side.lower() == "buy"
            
            # Get market info for decimals
            market = self._markets.get(coin, {})
            sz_decimals = market.get("sz_decimals", 0)
            
            # Round amount to correct decimals
            amount = round(amount, sz_decimals)
            
            # Place order based on type
            if order_type == "market":
                # Market order (IOC)
                order_result = self.exchange.market_open(
                    coin=coin,
                    is_buy=is_buy,
                    sz=amount,
                    slippage=0.01  # 1% slippage tolerance
                )
            else:
                # Limit order
                order_result = self.exchange.limit_open(
                    coin=coin,
                    is_buy=is_buy,
                    sz=amount,
                    limit_price=price,
                    order_type={"limit": {"tif": "Gtc"}}
                )
            
            # Parse result
            if order_result and order_result.get("status") == "ok":
                response = order_result.get("response", {})
                data = response.get("data", {})
                
                # Get filled info
                statuses = data.get("statuses", [])
                filled_price = price
                filled_amount = amount
                
                for status in statuses:
                    if "filled" in status:
                        filled = status["filled"]
                        filled_price = float(filled.get("avgPx", price))
                        filled_amount = float(filled.get("totalSz", amount))
                    elif "resting" in status:
                        # Limit order placed
                        pass
                
                return {
                    "success": True,
                    "order_id": str(data.get("oid", "")),
                    "filled_price": filled_price,
                    "filled_amount": filled_amount
                }
            else:
                error = order_result.get("response", {}).get("data", "Unknown error")
                return {"success": False, "error": str(error)}
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an order."""
        try:
            if not self.exchange:
                return False
            
            coin = self._normalize_symbol(pair)
            
            result = self.exchange.cancel(
                coin=coin,
                oid=int(order_id)
            )
            
            return result and result.get("status") == "ok"
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order(self, order_id: str, pair: str) -> Dict:
        """Get order status."""
        try:
            if not self.wallet_address:
                return {}
            
            # Get open orders
            open_orders = self.info.open_orders(self.wallet_address)
            
            for order in open_orders:
                if str(order.get("oid")) == order_id:
                    return {
                        "id": str(order["oid"]),
                        "status": "open",
                        "filled": 0,
                        "remaining": float(order.get("sz", 0)),
                        "price": float(order.get("limitPx", 0))
                    }
            
            # Order not found in open orders (might be filled/cancelled)
            return {"id": order_id, "status": "unknown"}
            
        except Exception as e:
            logger.error(f"Error fetching order: {e}")
            return {}
    
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Get open orders."""
        try:
            if not self.wallet_address:
                return []
            
            open_orders = self.info.open_orders(self.wallet_address)
            
            orders = []
            for order in open_orders:
                coin = order.get("coin", "")
                
                # Filter by pair if specified
                if pair and coin != self._normalize_symbol(pair):
                    continue
                
                orders.append({
                    "id": str(order.get("oid", "")),
                    "symbol": coin,
                    "side": "buy" if order.get("isBuy", False) else "sell",
                    "type": "limit",
                    "price": float(order.get("limitPx", 0)),
                    "amount": float(order.get("sz", 0)),
                    "filled": 0
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions."""
        try:
            if not self.wallet_address:
                return []
            
            user_state = self.info.user_state(self.wallet_address)
            positions = []
            
            if "assetPositions" in user_state:
                for pos in user_state["assetPositions"]:
                    if "position" in pos:
                        position = pos["position"]
                        size = float(position.get("szi", 0))
                        
                        if size != 0:
                            positions.append({
                                "symbol": position.get("coin", ""),
                                "side": "buy" if size > 0 else "sell",
                                "size": abs(size),
                                "entry_price": float(position.get("entryPx", 0)),
                                "unrealized_pnl": float(position.get("unrealizedPnl", 0)),
                                "leverage": float(position.get("leverage", {}).get("value", 1)),
                                "liquidation_price": float(position.get("liquidationPx", 0) or 0)
                            })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def set_leverage(self, pair: str, leverage: int) -> bool:
        """Set leverage for a pair."""
        try:
            if not self.exchange:
                return False
            
            coin = self._normalize_symbol(pair)
            
            result = self.exchange.update_leverage(
                leverage=leverage,
                coin=coin,
                is_cross=True  # Use cross margin
            )
            
            return result and result.get("status") == "ok"
            
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False
    
    def _normalize_symbol(self, pair: str) -> str:
        """Convert pair format to Hyperliquid symbol."""
        # BTC/USDC -> BTC, ETH/USDC -> ETH
        if "/" in pair:
            return pair.split("/")[0]
        return pair.upper()
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to Hyperliquid interval format."""
        timeframe_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "15m",  # Hyperliquid doesn't have 30m, use 15m
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w"
        }
        return timeframe_map.get(timeframe, "1h")
    
    def _calculate_lookback(self, timeframe: str, limit: int) -> int:
        """Calculate lookback hours for candle fetching."""
        timeframe_hours = {
            "1m": 1/60,
            "5m": 5/60,
            "15m": 15/60,
            "30m": 30/60,
            "1h": 1,
            "4h": 4,
            "1d": 24,
            "1w": 168
        }
        
        hours_per_candle = timeframe_hours.get(timeframe, 1)
        return int(limit * hours_per_candle) + 1
    
    def __repr__(self):
        return f"<HyperliquidExchange(testnet={self.testnet}, connected={self.connected})>"
