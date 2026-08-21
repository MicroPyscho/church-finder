import asyncio
import logging

from app.logging_config import configure_logging
from app.scheduler import start_scheduler, stop_scheduler
from app.config import settings

configure_logging()
logger = logging.getLogger("sanctuary.worker")


async def main():
    start_scheduler(crawl_hours=settings.CRAWL_INTERVAL_HOURS)
    logger.info("Worker started — scheduler running")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())