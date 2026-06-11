import asyncio
import sys
sys.path.insert(0, '.')

from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.core.engine import TradingEngine
from src.dashboard.server import TradingDashboard

async def main():
    setup_logger()
    config = load_config()
    
    # Start engine
    engine = TradingEngine(config)
    
    # Start dashboard
    dashboard = TradingDashboard(config, engine)
    
    # Run both
    await asyncio.gather(
        engine.start(),
        dashboard.start(host="0.0.0.0", port=8000)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
