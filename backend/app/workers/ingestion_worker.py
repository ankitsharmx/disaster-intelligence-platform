import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.session import AsyncSessionLocal
from app.integrations.weather import WeatherDemoSource, WeatherLiveSource
from app.integrations.earthquake import EarthquakeDemoSource, EarthquakeLiveSource
from app.integrations.fire import FireDemoSource
from app.integrations.alert_feed import AlertDemoSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingestion_worker")


async def run_ingestion_cycle():
    """Runs a single round of all registered data source adapters (Live public feeds and Demo sources)."""
    logger.info("Executing scheduled ingestion cycle for all active hazard adapters...")
    sources = [
        EarthquakeLiveSource(),
        WeatherLiveSource(),
        WeatherDemoSource(),
        EarthquakeDemoSource(),
        FireDemoSource(),
        AlertDemoSource(),
    ]

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for source in sources:
                    try:
                        res = await source.execute_run(session=session)
                        logger.info(f"[{source.name}] Status: {res['status']}, Records: {res['records_count']}")
                    except Exception as e:
                        logger.error(f"[{source.name}] Error during scheduled ingestion: {e}")
    except Exception as e:
        logger.warning(f"Database session unavailable in worker: {e}")
        # Run without session for verification
        for source in sources:
            res = await source.execute_run(session=None)
            logger.info(f"[Offline] [{source.name}] Status: {res['status']}, Records: {res['records_count']}")


async def main():
    logger.info("Ingestion worker started. Running initial sync...")
    await run_ingestion_cycle()


if __name__ == "__main__":
    asyncio.run(main())
