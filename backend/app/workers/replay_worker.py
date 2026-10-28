import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.replay_service import replay_engine
from app.workers.ingestion_worker import run_ingestion_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("replay_worker")


async def run_cli_replay(scenario: str, speed: float):
    logger.info(f"Starting Demo Replay Worker (Scenario: {scenario}, Speed: {speed}x)...")
    await replay_engine.start(scenario_filename=scenario, speed=speed)

    try:
        while True:
            await asyncio.sleep(1.0)
            status = replay_engine.get_status()
            logger.info(
                f"[Progress: {status['progress_percent']}%] "
                f"Offset: {status['current_offset_seconds']}s / {status['total_duration_seconds']}s | "
                f"Emitted: {status['events_emitted']}/{status['events_total']} events | "
                f"Status: {status['status']}"
            )
            if status["status"] in ("completed", "stopped", "error"):
                break
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Resetting replay...")
        await replay_engine.reset()

    logger.info("Demo Replay Worker finished.")


async def run_daemon_worker():
    """Worker daemon mode executing recurring external data ingestion and listening for replay triggers."""
    logger.info("Worker daemon started. Executing initial multi-hazard ingestion...")
    try:
        await run_ingestion_cycle()
    except Exception as e:
        logger.warning(f"Initial worker ingestion cycle had warning: {e}")

    logger.info("Worker daemon entering recurring schedule (sync cycle every 60s)...")
    sync_interval = 60.0  # seconds
    last_sync = asyncio.get_event_loop().time()

    while True:
        await asyncio.sleep(5.0)
        now = asyncio.get_event_loop().time()
        if now - last_sync >= sync_interval:
            try:
                await run_ingestion_cycle()
            except Exception as e:
                logger.error(f"Error during periodic worker ingestion cycle: {e}")
            last_sync = now


def main():
    parser = argparse.ArgumentParser(description="Disaster Management System - Demo Replay Worker")
    parser.add_argument("--scenario", default="monsoon_flood_scenario.json", help="Scenario JSON filename")
    parser.add_argument("--speed", type=float, default=2.0, help="Replay speed multiplier (e.g., 2.0, 5.0, 10.0)")
    parser.add_argument("--mode", choices=["cli", "daemon"], default="cli", help="Worker execution mode")

    args = parser.parse_args()

    if args.mode == "cli":
        asyncio.run(run_cli_replay(args.scenario, args.speed))
    else:
        asyncio.run(run_daemon_worker())


if __name__ == "__main__":
    main()
