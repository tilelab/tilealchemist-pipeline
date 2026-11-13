"""HTTP Range requests against the source archive, with retries.

The only retry layer: sessions are plain `requests.Session()`s.
"""
import io
import sys
import time
from collections.abc import Callable
from typing import BinaryIO

import requests
from tilealchemist.console import log
from tilealchemist.console.throttle import UpdateLineThrottle

from tilealchemist_pipeline.fetch.backoff import backoff_delay

# Enough for the transient CDN errors of a cold-cache stampede.
MAX_RANGE_ATTEMPTS: int = 6
RANGE_RETRY_BASE_DELAY: float = 2.0
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# (connect, read), in seconds.
REQUEST_TIMEOUT: tuple[float, float] = (10, 60)

READ_SIZE: int = 1024 * 1024

# A crawling connection never trips the read timeout, and a new one is
# usually fast.
MIN_FETCH_RATE: int = 2 * 1024 * 1024
SLOW_WINDOW_SECONDS: float = 30.0
MAX_SLOW_RECONNECTS: int = 3


class DownloadProgress:
    """Prints a download's progress at most once per interval.

    Attributes:
        total_bytes: The download's expected size.
        label: The download's name in the line.
        throttle: Limits the lines.
    """

    total_bytes: int
    label: str
    throttle: UpdateLineThrottle

    def __init__(self, total_bytes: int, interval: float, label: str) -> None:
        self.total_bytes = total_bytes
        self.label = label
        self.throttle = UpdateLineThrottle(interval, fire_immediately=True)

    def update(self, downloaded: int) -> None:
        """Reports `downloaded` bytes so far, if a line is due."""
        if not self.throttle.due():
            return
        percent: float = ((100 * downloaded / self.total_bytes)
                          if self.total_bytes else 100.0)
        print(f"update: downloading {self.label}: "
              f"{downloaded}/{self.total_bytes} bytes ({percent:.1f}%)",
              file=sys.stderr)


class _RetryableFailure(Exception):
    """A failed attempt worth retrying.

    Attributes:
        detail: What went wrong, for the warning.
        response: The failed response, or None if none arrived.
        final: What to raise once the attempts run out.
    """

    detail: str
    response: requests.Response | None
    final: Exception

    def __init__(self, detail: str, response: requests.Response | None,
                 final: Exception) -> None:
        super().__init__(detail)
        self.detail = detail
        self.response = response
        self.final = final


class _SlowConnection(Exception):
    """An attempt abandoned for being too slow.

    Attributes:
        detail: How slow, for the warning.
    """

    detail: str

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _attempt_fetch_range(session: requests.Session, url: str,
                         range_header: str, received: int, dest: BinaryIO,
                         on_progress: Callable[[int], None] | None,
                         min_rate: float | None) -> None:
    """Makes one ranged request, writing the body to `dest` as it arrives.

    Args:
        session: The session to use.
        url: Absolute URL of the archive.
        range_header: The `bytes=start-end` to ask for.
        received: Bytes earlier attempts delivered, for the running total.
        dest: The file to write to.
        on_progress: Called with the running total, or None.
        min_rate: Bytes per second each SLOW_WINDOW_SECONDS must average, or
            None for any rate.

    Raises:
        _RetryableFailure: On a connection error, a retryable status, a
            status other than 206, or a connection dropped mid-body.
        _SlowConnection: If a window averaged under `min_rate`.
        requests.HTTPError: On a status not worth retrying.
    """
    response: requests.Response
    try:
        response = session.get(url, headers={"Range": range_header},
                               timeout=REQUEST_TIMEOUT, stream=True)
    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as error:
        raise _RetryableFailure(
            f"request for range {range_header} failed "
            f"({error.__class__.__name__})", None, error) from error
    # Releases the connection on a raise, before the caller's backoff sleeps.
    with response:
        status: int = response.status_code

        if status in RETRYABLE_STATUS_CODES:
            raise _RetryableFailure(
                f"got HTTP {status} for range {range_header}", response,
                requests.HTTPError(f"HTTP {status} ({response.reason}) for "
                                   f"range {range_header} of {url}",
                                   response=response))

        response.raise_for_status()
        if status != 206:
            raise _RetryableFailure(
                f"got HTTP {status} instead of 206 for range {range_header}",
                response,
                RuntimeError(
                    f"expected HTTP 206 Partial Content for ranged request "
                    f"({range_header}) after {MAX_RANGE_ATTEMPTS} attempts, "
                    f"got {status}: server ignored the Range header and would "
                    f"send the entire archive instead of just this range"))

        downloaded: int = received
        window_start: float = time.monotonic()
        window_bytes: int = 0
        piece: bytes
        try:
            for piece in response.iter_content(chunk_size=READ_SIZE):
                if not piece:
                    continue
                dest.write(piece)
                downloaded += len(piece)
                if on_progress is not None:
                    on_progress(downloaded)
                if min_rate is None:
                    continue
                window_bytes += len(piece)
                elapsed: float = time.monotonic() - window_start
                if elapsed < SLOW_WINDOW_SECONDS:
                    continue
                if window_bytes < min_rate * elapsed:
                    # Leaving mid-body closes the connection instead of
                    # pooling it, so the next attempt gets a new one.
                    rate: float = window_bytes / elapsed / 1024
                    raise _SlowConnection(
                        f"connection averaged {rate:.0f} KiB/s over "
                        f"{elapsed:.0f}s after {downloaded} bytes")
                window_start = time.monotonic()
                window_bytes = 0
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError) as error:
            # No response to read a Retry-After from: jitter alone.
            raise _RetryableFailure(
                f"connection dropped after {downloaded} bytes "
                f"({error.__class__.__name__})", None, error) from error


def _warn_retry(retry_label: str, detail: str, attempt: int,
                delay: float) -> None:
    """Warns that attempt `attempt` failed and the next follows in `delay`s."""
    log.warning(f"{retry_label} retry", f"{detail} (attempt "
                f"{attempt}/{MAX_RANGE_ATTEMPTS}), retrying in {delay:.0f}s")


def _warn_reconnect(retry_label: str, detail: str, reconnect: int) -> None:
    """Warns that a slow attempt is replaced by reconnect `reconnect`."""
    then: str = (", keeping the next one at any speed"
                 if reconnect == MAX_SLOW_RECONNECTS else "")
    log.warning(f"{retry_label} reconnect",
                f"{detail}, under {MIN_FETCH_RATE // 1024} KiB/s; reconnecting "
                f"({reconnect}/{MAX_SLOW_RECONNECTS}{then})")


def fetch_range(session: requests.Session, url: str, offset: int, length: int,
                dest: BinaryIO, retry_label: str,
                on_progress: Callable[[int], None] | None = None) -> None:
    """Streams a byte range into `dest`, retrying what is worth retrying.

    An attempt under MIN_FETCH_RATE is dropped for a new connection, up to
    MAX_SLOW_RECONNECTS times and without using up an attempt; after that any
    rate is accepted. Each retry asks only for the bytes still missing.

    Args:
        session: The session to use.
        url: Absolute URL of the archive.
        offset: First byte to read.
        length: Bytes to read.
        dest: The file to write to, from its current position.
        retry_label: The fetch's name in warnings.
        on_progress: Called with the running total, or None.

    Raises:
        requests.HTTPError: If the server kept failing or failed for good.
        RuntimeError: If the server ignored the Range header.
    """
    attempt: int = 1
    reconnects: int = 0
    dest_start: int = dest.tell()
    while True:
        received: int = dest.tell() - dest_start
        if received == length:
            # A slow window can close on the body's last piece.
            break
        range_header: str = f"bytes={offset + received}-{offset + length - 1}"
        min_rate: float | None = (MIN_FETCH_RATE
                                  if reconnects < MAX_SLOW_RECONNECTS else None)
        try:
            _attempt_fetch_range(session, url, range_header, received, dest,
                                 on_progress, min_rate)
            break
        except _SlowConnection as slow:
            # Nothing failed, so no backoff.
            reconnects += 1
            _warn_reconnect(retry_label, slow.detail, reconnects)
        except _RetryableFailure as failure:
            if attempt == MAX_RANGE_ATTEMPTS:
                raise failure.final from failure
            delay: float = backoff_delay(attempt, failure.response,
                                         RANGE_RETRY_BASE_DELAY)
            _warn_retry(retry_label, failure.detail, attempt, delay)
            time.sleep(delay)
            attempt += 1


def fetch_bytes(session: requests.Session, url: str, offset: int, length: int,
                retry_label: str,
                on_progress: Callable[[int], None] | None = None) -> bytes:
    """Returns a byte range, fetched like fetch_range() does."""
    buffer: io.BytesIO = io.BytesIO()
    fetch_range(session, url, offset, length, buffer, retry_label,
                on_progress)
    return buffer.getvalue()
