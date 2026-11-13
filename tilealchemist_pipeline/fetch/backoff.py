"""Retry delays for ranged requests."""
import random

import requests


def backoff_delay(attempt: int, response: requests.Response | None,
                  base_delay: float) -> float:
    """Returns how many seconds to wait before retrying a request.

    The server's Retry-After wins. Otherwise the delay doubles per attempt,
    with jitter so workers throttled together don't retry in lockstep.

    Args:
        attempt: 1 for the first retry, 2 for the second, and so on.
        response: The failed response, or None if none arrived.
        base_delay: The first retry's delay, in seconds.
    """
    return (_server_requested_delay(response)
            or base_delay * 2 ** (attempt - 1) * random.uniform(1.0, 1.5))


def _server_requested_delay(response: requests.Response | None) -> float | None:
    """Returns the response's Retry-After in seconds, if it has a valid one."""
    if response is None:
        return None
    retry_after: str | None = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except ValueError:
        return None
