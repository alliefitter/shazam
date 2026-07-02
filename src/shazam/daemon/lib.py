from collections.abc import Callable
from logging import getLogger

from httpx import HTTPError, Response

logger = getLogger(__name__)


def retryable_request(request_callback: Callable[[], Response]):
    for attempt in range(3):
        try:
            return request_callback()
        except HTTPError:
            if attempt < 2:
                logger.warning("album cover download timed out, retrying")
            else:
                raise


def oxford_join(names: list[str]) -> str:
    match names:
        case []:
            return ""
        case [name]:
            return name
        case [a, b]:
            return f"{a} and {b}"
        case _:
            return ", ".join(names[:-1]) + f", and {names[-1]}"
