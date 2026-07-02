import json
import logging
from io import BytesIO
from threading import Event
from time import time
from typing import Any

import numpy as np
from acrcloud.recognizer import ACRCloudRecognizer
from scipy.io.wavfile import write as wav_write
from sounddevice import InputStream

from shazam.lib.config import get_config

SAMPLE_RATE = 48000
CHANNELS = 2
DURATION = 10
DEVICE = 1

CHUNK = 2400  # 50ms at 48kHz
INT32_MAX = 2**31
INTER_SONG_SECONDS = 2.0
ACTIVE_SONG_SECONDS = 3.0
SILENCE_CHUNKS = int(INTER_SONG_SECONDS * SAMPLE_RATE / CHUNK)
ACTIVE_SONG_CHUNKS = int(ACTIVE_SONG_SECONDS * SAMPLE_RATE / CHUNK)
SILENCE_THRESHOLD = 0.001  # normalized RMS
SONG_CHANGE_TIMEOUT = 45
RESET_TIMEOUT = 300.0
BLANK_TIMEOUT = 900.0

logger = logging.getLogger(__name__)
config = get_config()


class Recognition:
    def __init__(self):
        self.recognizer = ACRCloudRecognizer(
            {
                "host": config.acr_host,
                "access_key": config.acr_access_key,
                "access_secret": config.acr_access_secret,
                "timeout": 10,
            }
        )
        self._stop_listening = Event()
        self._silent_count = 0
        self._is_silent = False
        self._has_song_potentially_changed = False
        self._record_chunks: list[np.ndarray] = []
        self._record_samples_needed = 0
        self._record_done = Event()
        self._stream = InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            device=DEVICE,
            dtype="int32",
            blocksize=CHUNK,
            callback=self._callback,
        )
        self._historic_rms = []
        self._last_recognition_time = 0.0
        self._silence_started_at = 0.0

    @property
    def should_record(self) -> bool:
        return (
            not self._is_silent
            and (
                len(self._historic_rms) > ACTIVE_SONG_CHUNKS
                and sum(self._historic_rms) / len(self._historic_rms)
                > SILENCE_THRESHOLD
            )
            and (
                self._has_song_potentially_changed
                or time() - self._last_recognition_time > SONG_CHANGE_TIMEOUT
            )
        )

    @property
    def should_blank(self) -> bool:
        return (
            self._silence_started_at > 0.0
            and time() - self._silence_started_at > BLANK_TIMEOUT
        )

    @property
    def should_reset(self) -> bool:
        if self._silence_started_at > 0.0:
            logger.info(
                f"Input has been silent for {time() - self._silence_started_at:.2f}"
            )
        return (
            self._silence_started_at > 0.0
            and time() - self._silence_started_at > RESET_TIMEOUT
        )

    def start(self) -> None:
        logger.info("Starting audio stream")
        self._stream.start()

    def stop(self) -> None:
        logger.info("Stopping audio stream")
        self._stream.stop()
        self._stream.close()
        self._stop_listening.set()
        self._record_done.set()

    def _callback(self, indata: np.ndarray, frames: int, *_) -> None:
        rms = np.sqrt(np.mean(indata.astype(np.float64) ** 2)) / INT32_MAX
        if rms < SILENCE_THRESHOLD:
            if self._silence_started_at == 0.0:
                self._silence_started_at = time()
            self._silent_count += 1
            if self._silent_count == SILENCE_CHUNKS:
                self._historic_rms = []
                logger.info("Potential song change detected")
                self._has_song_potentially_changed = True

            if self._silent_count > SILENCE_CHUNKS:
                self._is_silent = True

        else:
            self._silence_started_at = 0.0
            self._historic_rms.append(rms)
            self._silent_count = 0
            self._is_silent = False
            if self.should_record and not self._stop_listening.is_set():
                logger.info(
                    f"Stop listening. Avg RMS: {sum(self._historic_rms) / len(self._historic_rms)}"
                )
                self._stop_listening.set()

        if self._record_samples_needed > 0:
            self._record_chunks.append(indata.copy())
            self._record_samples_needed -= frames
            if self._record_samples_needed <= 0:
                logger.info("Acquired enough chunks")
                self._record_done.set()

    def wait(self) -> bool:
        self._stop_listening.clear()
        self._stop_listening.wait(timeout=SONG_CHANGE_TIMEOUT)
        should_record = self.should_record
        self._silent_count = 0
        self._historic_rms = []
        self._has_song_potentially_changed = False

        return should_record

    def record(self) -> dict[str, Any] | None:
        logger.info(f"Recording {DURATION} of audio")
        self._record_chunks = []
        self._record_done.clear()
        self._record_samples_needed = int(DURATION * SAMPLE_RATE)
        self._record_done.wait()
        logger.info("Recording complete, sending to AudD")
        recording = np.concatenate(self._record_chunks)
        buffer = BytesIO()
        wav_write(buffer, SAMPLE_RATE, recording)
        buffer.seek(0)
        raw_result = self.recognizer.recognize_by_filebuffer(buffer.getvalue(), 0)
        logger.debug(raw_result)
        if raw_result is not None:
            self._last_recognition_time = time()
            result = json.loads(raw_result)
            status_in_result = "status" in result
            return (
                result if status_in_result and result["status"]["code"] == 0 else None
            )

        return None
