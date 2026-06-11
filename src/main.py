"""
Crypto Trading Agent - Main Entry Point
"""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from src.core.engine import TradingEngine
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main():
    """Main entry point for the trading agent."""
    
    # Setup logging
    setup_logger()
    logger.info("Starting Crypto Trading Agent...")
    
    # Load configuration
    config = load_config()
    
    # Create trading engine
    engine = TradingEngine(config)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping engine...")
        engine.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start engine
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        logger.info("Trading agent stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
