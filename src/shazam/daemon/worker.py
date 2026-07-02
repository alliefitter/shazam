import logging
from asyncio import (
    Event,
    all_tasks,
    create_task,
    current_task,
    gather,
    new_event_loop,
    set_event_loop,
)
from signal import SIGINT, SIGTERM, signal
from threading import Thread
from types import FrameType
from typing import Any

from httpx import AsyncClient, HTTPError

from shazam.daemon.recognition import Recognition
from shazam.daemon.song_lookup import SongInfo, SongLookup
from shazam.daemon.ui.screen import Screen
from shazam.lib.db import DataMapper, Song

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, screen: Screen, db: DataMapper, client: AsyncClient):
        self.screen = screen
        self.lookup = SongLookup(
            db,
            client,
        )
        self.db = db
        self.recognition = Recognition()
        self.loop = new_event_loop()
        self._thread = Thread(target=self._run, daemon=True)
        self._shutdown = Event()
        self.current_song: SongInfo | None = None
        self.previous_song: SongInfo | None = None

    def setup(self):
        def _shutdown(signum: int, frame: FrameType | None):
            self.stop()
            self.screen.root.quit()

        signal(SIGINT, _shutdown)
        signal(SIGTERM, _shutdown)

    def start(self):
        self._thread.start()

    def stop(self):
        self.loop.call_soon_threadsafe(self._shutdown.set)

    async def _cleanup(self):
        tasks = [t for t in all_tasks(self.loop) if t is not current_task()]
        for t in tasks:
            t.cancel()
        await gather(*tasks, return_exceptions=True)

    async def _loop(self):
        logger.info("worker loop started")
        self.recognition.start()
        try:
            while True:
                try:
                    logger.info("Listening for music")
                    should_record = self.recognition.wait()
                    if should_record:
                        logger.info("Detected music. Recording")
                        if self.screen.is_blanked:
                            self.screen.unblank()
                        result = self.recognition.record()
                        if result:
                            await self._set_song(result)
                    if self.recognition.should_reset:
                        logger.info("Reset")
                        self.screen.reset()
                        self.current_song = None
                        self.previous_song = None

                    if self.recognition.should_blank:
                        self.screen.blank()
                except HTTPError as e:
                    logger.error("HTTP error", exc_info=e)

                except Exception as e:
                    logger.error("Unexpected error", exc_info=e)
                    self.stop()
                    self.screen.root.quit()
                    raise
        finally:
            self.recognition.stop()

    def _run(self):
        async def _main():
            task = create_task(self._loop())
            try:
                await self._shutdown.wait()
            finally:
                task.cancel()
                await self._cleanup()

        set_event_loop(self.loop)
        self.loop.run_until_complete(_main())

    async def _set_song(self, result: dict[str, Any]):
        song = await self.lookup.get_song_info(result)
        if not song.title or not song.artist:
            logger.warning("No title or artist found")
            return

        checksums_match = False
        match_has_new_cover = False
        if self.current_song:
            checksums_match = song.checksum == self.current_song.checksum
            match_has_new_cover = (
                checksums_match
                and self.current_song.album_cover is None
                and song.album_cover is not None
            )

        if not checksums_match or match_has_new_cover:
            logger.info(
                f"Displaying new song {song.title} - {song.artist} - {song.album}"
            )
            if not checksums_match:
                self.previous_song = self.current_song

            self.screen.set_song(song, self.previous_song)
            if not song.album_cover:
                song = await self.lookup.get_album_cover(song)
                self.screen.set_song(song, self.previous_song)

            self.db.log_song(song.title, song.artist, song.album, song.album_cover)

            self.current_song = song
