r"""Running tools whose \r-redrawn progress bars flood logs."""
import io
import queue
import re
import subprocess
import sys
import threading
import time
from typing import cast

from tilealchemist.console.throttle import UpdateLineThrottle

_TERMINATOR: re.Pattern[bytes] = re.compile(rb"(\r|\n)")


def run_throttled(command: list[str], interval: float, label: str) -> int:
    r"""Returns `command`'s exit code, its output copied to stderr.

    Log viewers such as GitHub Actions' print every \r redraw as a line of
    its own. \n lines pass through at once; of the redraws only the latest is
    kept, printed once `interval` seconds have passed, and dropped by the
    next \n line. After `interval` seconds without output, the held redraw
    goes out, or else an `update:` line saying how long the tool has run.

    Args:
        command: The tool and its arguments.
        interval: Minimum seconds between two printed redraws, and the
            silence after which a line goes out.
        label: The tool's name in `update:` lines.
    """
    process: subprocess.Popen[bytes]
    with subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as process:
        source: io.BufferedReader = cast(io.BufferedReader, process.stdout)
        sink: io.BufferedWriter = cast(io.BufferedWriter, sys.stderr.buffer)
        # Read on a thread, so silence can be timed on every platform.
        chunks: queue.Queue[bytes] = queue.Queue()
        threading.Thread(target=_read_chunks, args=(source, chunks),
                         daemon=True).start()
        started: float = time.monotonic()
        throttle: UpdateLineThrottle = UpdateLineThrottle(interval)
        pending: bytes | None = None  # The latest redraw not printed yet.
        rest: bytes = b""  # Text whose terminator has not arrived yet.
        chunk: bytes
        pieces: list[bytes]
        text: bytes
        terminator: bytes
        while True:
            try:
                chunk = chunks.get(timeout=interval)
            except queue.Empty:
                # Silent for an interval, so the last line is at least as old.
                throttle.due()
                if pending is None:
                    pending = (f"update: {label}: still running after "
                               f"{_duration(time.monotonic() - started)}"
                               ).encode()
                sink.write(pending + b"\n")
                sink.flush()
                pending = None
                continue
            if not chunk:
                break
            *pieces, rest = _TERMINATOR.split(rest + chunk)
            for text, terminator in zip(pieces[::2], pieces[1::2]):
                if terminator == b"\n":
                    sink.write(text + b"\n")
                    pending = None
                elif text.strip():  # A blank redraw only erases the last.
                    pending = text
            if pending is not None and throttle.due():
                sink.write(pending + b"\n")
                pending = None
            sink.flush()
        leftover: bytes | None
        for leftover in (pending, rest):
            if leftover:
                sink.write(leftover + b"\n")
        sink.flush()
    return process.returncode


def _read_chunks(source: io.BufferedReader,
                 chunks: queue.Queue[bytes]) -> None:
    """Puts `source`'s output into `chunks`, then b"" once it ends."""
    chunk: bytes
    while chunk := source.read1(65536):
        chunks.put(chunk)
    chunks.put(b"")


def _duration(seconds: float) -> str:
    """Returns `seconds` as `45s` or `3m 15s`."""
    minutes: int
    remainder: int
    minutes, remainder = divmod(round(seconds), 60)
    return f"{minutes}m {remainder}s" if minutes else f"{remainder}s"
