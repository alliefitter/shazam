import asyncio
import logging

from httpx import AsyncClient

from shazam.daemon.ui.screen import Screen
from shazam.daemon.worker import Worker
from shazam.lib.db import DataMapper, get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

if __name__ == "__main__":
    log.info("starting")
    screen = Screen()
    client = AsyncClient()
    worker = Worker(screen, DataMapper(get_session()), client)
    worker.setup()
    worker.start()

    try:
        screen.start()
    finally:
        log.info("shutting down")
        worker.stop()
        asyncio.run(client.aclose())
