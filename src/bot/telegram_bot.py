"""
Telegram Bot - Control and monitor trading agent via Telegram.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from loguru import logger

try:
    from telegram import Update, BotCommand
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        ContextTypes,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")


class TradingTelegramBot:
    """Telegram bot for controlling the trading agent."""
    
    def __init__(self, config: Dict, engine=None):
        self.config = config
        self.engine = engine
        self.bot_token = config.get("bot_token")
        self.chat_id = config.get("chat_id")
        self.authorized_users = config.get("authorized_users", [])
        self.app: Optional['Application'] = None
        self.running = False
    
    async def start(self):
        """Start the Telegram bot."""
        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram bot not available - install python-telegram-bot")
            return
        
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return
        
        # Create application
        self.app = Application.builder().token(self.bot_token).build()
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("balance", self._cmd_balance))
        self.app.add_handler(CommandHandler("positions", self._cmd_positions))
        self.app.add_handler(CommandHandler("trades", self._cmd_trades))
        self.app.add_handler(CommandHandler("start_trading", self._cmd_start_trading))
        self.app.add_handler(CommandHandler("stop_trading", self._cmd_stop_trading))
        self.app.add_handler(CommandHandler("strategy", self._cmd_strategy))
        self.app.add_handler(CommandHandler("stats", self._cmd_stats))
        self.app.add_handler(CommandHandler("config", self._cmd_config))
        
        # Set commands
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("status", "Trading status"),
            BotCommand("balance", "Account balance"),
            BotCommand("positions", "Open positions"),
            BotCommand("trades", "Recent trades"),
            BotCommand("start_trading", "Start trading"),
            BotCommand("stop_trading", "Stop trading"),
            BotCommand("strategy", "Change strategy"),
            BotCommand("stats", "Trading statistics"),
            BotCommand("config", "Show config"),
        ]
        
        await self.app.bot.set_my_commands(commands)
        
        # Start polling
        self.running = True
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the Telegram bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self.running = False
        logger.info("Telegram bot stopped")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        if not self.authorized_users:
            return True  # No restriction if list is empty
        return user_id in self.authorized_users
    
    async def _send_message(self, chat_id: str, text: str):
        """Send message to Telegram."""
        if self.app and self.app.bot:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
    
    async def send_notification(self, message: str):
        """Send notification to configured chat."""
        if self.chat_id:
            await self._send_message(self.chat_id, message)
    
    # Command handlers
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        welcome = """
🤖 <b>Crypto Trading Agent</b>

Welcome! I'm your trading assistant.

Commands:
/status - Trading status
/balance - Account balance
/positions - Open positions
/start_trading - Start trading
/stop_trading - Stop trading
/help - Show all commands

Use /help for detailed information.
        """
        await update.message.reply_text(welcome, parse_mode="HTML")
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        help_text = """
📋 <b>Available Commands</b>

<b>Monitoring:</b>
/status - Current trading status
/balance - Account balance
/positions - Open positions
/trades - Recent trades
/stats - Trading statistics

<b>Control:</b>
/start_trading - Start trading
/stop_trading - Stop trading
/strategy [name] - Change strategy

<b>Configuration:</b>
/config - Show current config

<b>Strategies:</b>
• sma_crossover - SMA Crossover
• rsi - RSI (Relative Strength Index)
• macd - MACD
• bollinger_bands - Bollinger Bands
        """
        await update.message.reply_text(help_text, parse_mode="HTML")
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine:
            await update.message.reply_text("❌ Trading engine not connected")
            return
        
        stats = self.engine.get_stats()
        
        status = f"""
📊 <b>Trading Status</b>

⏱️ <b>Uptime:</b> {stats.get('uptime', '0:00:00')}
🔄 <b>Running:</b> {'✅ Yes' if self.engine.running else '❌ No'}

💰 <b>Portfolio:</b>
• Value: ${stats.get('portfolio_value', 0):,.2f}
• Positions: {stats.get('open_positions', 0)}

📈 <b>Performance:</b>
• Trades: {stats.get('trades_executed', 0)}
• P/L: ${stats.get('total_profit_loss', 0):,.2f}
        """
        await update.message.reply_text(status, parse_mode="HTML")
    
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine or not self.engine.portfolio:
            await update.message.reply_text("❌ Portfolio not available")
            return
        
        portfolio_stats = self.engine.portfolio.get_stats()
        
        balance = f"""
💰 <b>Account Balance</b>

💵 <b>Available:</b> ${portfolio_stats.get('available_balance', 0):,.2f}
📊 <b>Total Value:</b> ${portfolio_stats.get('total_value', 0):,.2f}

📈 <b>Performance:</b>
• Initial: ${portfolio_stats.get('initial_value', 0):,.2f}
• P/L: ${portfolio_stats.get('total_pnl', 0):,.2f}
• Win Rate: {portfolio_stats.get('win_rate', 0):.1%}
• Drawdown: {portfolio_stats.get('drawdown', 0):.1%}
        """
        await update.message.reply_text(balance, parse_mode="HTML")
    
    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine or not self.engine.portfolio:
            await update.message.reply_text("❌ Portfolio not available")
            return
        
        positions = self.engine.portfolio.get_open_positions()
        
        if not positions:
            await update.message.reply_text("📭 No open positions")
            return
        
        text = "📊 <b>Open Positions</b>\n\n"
        
        for pos in positions:
            pnl_emoji = "🟢" if pos.unrealized_pnl >= 0 else "🔴"
            text += f"""
{pnl_emoji} <b>{pos.pair}</b>
• Side: {pos.side.upper()}
• Size: {pos.amount:.4f}
• Entry: ${pos.entry_price:,.2f}
• Current: ${pos.current_price:,.2f}
• P/L: ${pos.unrealized_pnl:,.2f} ({pos.unrealized_pnl_percentage:.1%})
• SL: ${pos.stop_loss:,.2f if pos.stop_loss else 'N/A'}
• TP: ${pos.take_profit:,.2f if pos.take_profit else 'N/A'}
            """
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    async def _cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine or not self.engine.portfolio:
            await update.message.reply_text("❌ Portfolio not available")
            return
        
        trades = self.engine.portfolio.get_closed_positions()[-10:]  # Last 10
        
        if not trades:
            await update.message.reply_text("📭 No trades yet")
            return
        
        text = "📜 <b>Recent Trades</b>\n\n"
        
        for trade in trades:
            pnl_emoji = "🟢" if trade.final_pnl >= 0 else "🔴"
            text += f"{pnl_emoji} {trade.pair} | {trade.side} | ${trade.final_pnl:,.2f}\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    async def _cmd_start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_trading command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine:
            await update.message.reply_text("❌ Trading engine not available")
            return
        
        if self.engine.running:
            await update.message.reply_text("⚠️ Trading already running")
            return
        
        # Start engine in background
        asyncio.create_task(self.engine.start())
        await update.message.reply_text("✅ Trading started!")
    
    async def _cmd_stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_trading command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine:
            await update.message.reply_text("❌ Trading engine not available")
            return
        
        self.engine.stop()
        await update.message.reply_text("✅ Trading stopped!")
    
    async def _cmd_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /strategy command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            # Show current strategy
            current = self.config.get("strategy", {}).get("name", "unknown")
            await update.message.reply_text(f"📊 Current strategy: <b>{current}</b>", parse_mode="HTML")
            return
        
        strategy_name = context.args[0].lower()
        available = ["sma_crossover", "rsi", "macd", "bollinger_bands"]
        
        if strategy_name not in available:
            await update.message.reply_text(f"❌ Unknown strategy. Available: {', '.join(available)}")
            return
        
        # Update config
        self.config["strategy"]["name"] = strategy_name
        
        # Reinitialize strategy if engine is running
        if self.engine:
            from src.strategies import get_strategy
            self.engine.strategy = get_strategy(strategy_name, self.config["strategy"]["params"])
        
        await update.message.reply_text(f"✅ Strategy changed to: <b>{strategy_name}</b>", parse_mode="HTML")
    
    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        if not self.engine:
            await update.message.reply_text("❌ Trading engine not available")
            return
        
        stats = self.engine.get_stats()
        portfolio_stats = self.engine.portfolio.get_stats() if self.engine.portfolio else {}
        
        text = f"""
📈 <b>Trading Statistics</b>

⏱️ <b>Session:</b>
• Uptime: {stats.get('uptime', '0:00:00')}
• Trades: {stats.get('trades_executed', 0)}

💰 <b>Portfolio:</b>
• Value: ${portfolio_stats.get('total_value', 0):,.2f}
• P/L: ${portfolio_stats.get('total_pnl', 0):,.2f}
• Win Rate: {portfolio_stats.get('win_rate', 0):.1%}
• Drawdown: {portfolio_stats.get('drawdown', 0):.1%}

📊 <b>Positions:</b>
• Open: {portfolio_stats.get('open_positions', 0)}
• Closed: {portfolio_stats.get('closed_positions', 0)}
        """
        await update.message.reply_text(text, parse_mode="HTML")
    
    async def _cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        trading = self.config.get("trading", {})
        strategy = self.config.get("strategy", {})
        risk = self.config.get("risk", {})
        
        text = f"""
⚙️ <b>Configuration</b>

📊 <b>Trading:</b>
• Pairs: {', '.join(trading.get('pairs', []))}
• Timeframe: {trading.get('timeframe', '1h')}
• Max Positions: {trading.get('max_positions', 5)}
• Risk/Trade: {trading.get('risk_per_trade', 0.02):.1%}

📈 <b>Strategy:</b>
• Name: {strategy.get('name', 'unknown')}
• Params: {strategy.get('params', {})}

🛡️ <b>Risk Management:</b>
• Stop Loss: {risk.get('stop_loss_pct', 0.05):.1%}
• Take Profit: {risk.get('take_profit_pct', 0.10):.1%}
• Max Drawdown: {risk.get('max_drawdown', 0.20):.1%}
        """
        await update.message.reply_text(text, parse_mode="HTML")
    
    def __repr__(self):
        return f"<TradingTelegramBot(running={self.running})>"
