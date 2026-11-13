"""go-pmtiles' `pmtiles` binary, at a pinned release.

The merge runs `pmtiles merge`. The pinned release is downloaded once into
the cache and checked against its hash, so upstream releases can't change a
merge. TILEALCHEMIST_PMTILES names a binary to use instead.
"""
import hashlib
import io
import os
import platform
import stat
import sys
import tarfile
import zipfile
from typing import IO, BinaryIO

import requests

VERSION: str = "1.31.2"

OVERRIDE_VARIABLE: str = "TILEALCHEMIST_PMTILES"

# The cache directory's name, in the platform's per-user cache.
CACHE_NAME: str = "tilealchemist"

RELEASE_URL: str = ("https://github.com/protomaps/go-pmtiles/releases/download/"
                    f"v{VERSION}")

# Release asset and SHA-256 by (system, machine).
ASSETS: dict[tuple[str, str], tuple[str, str]] = {
    ("Darwin", "arm64"): (
        f"go-pmtiles-{VERSION}_Darwin_arm64.zip",
        "40528f7f616fcbf91207cd48c8fc023d213f6d86c0cbf1f748732803d1880f3d"),
    ("Darwin", "x86_64"): (
        f"go-pmtiles-{VERSION}_Darwin_x86_64.zip",
        "1f0dc02eee6c58312dd6c509faee1b5c32f0596568af1bf51f1b034e7a88a65b"),
    ("Linux", "arm64"): (
        f"go-pmtiles_{VERSION}_Linux_arm64.tar.gz",
        "f8bd47e7ea866863489cad588fbaf2f31f42e5821f7a03f009b3769f05801cb1"),
    ("Linux", "x86_64"): (
        f"go-pmtiles_{VERSION}_Linux_x86_64.tar.gz",
        "3ed7dbf4ec2e6dfe5e25b6f70d1ffc932729f93c86db353bf514dd71010a312f"),
    ("Windows", "arm64"): (
        f"go-pmtiles_{VERSION}_Windows_arm64.zip",
        "8780a17453c63af757917a694cbbb50b943db89cc3f1b07e6fd62c1ff8e6963b"),
    ("Windows", "x86_64"): (
        f"go-pmtiles_{VERSION}_Windows_x86_64.zip",
        "a658baa4d7e55020aef6ca17bd9ff9faa1582671266b36f58c52db0ac8e785a1"),
}

# Other lowercased platform.machine() names for a release's machine.
MACHINE_ALIASES: dict[str, str] = {"aarch64": "arm64", "amd64": "x86_64"}


def pmtiles_command() -> str:
    """Returns the `pmtiles` executable, downloading it if needed.

    Raises:
        RuntimeError: If no release is pinned for this platform, or the
            download doesn't match its hash.
        requests.HTTPError: If the download fails.
    """
    override: str | None = os.environ.get(OVERRIDE_VARIABLE)
    if override:
        return override
    executable: str = "pmtiles.exe" if sys.platform == "win32" else "pmtiles"
    path: str = os.path.join(_cache_dir(), "bin", f"pmtiles-{VERSION}",
                             executable)
    if not os.path.isfile(path):
        _install(path)
    return path


def _cache_dir() -> str:
    """Returns the platform's per-user cache directory for tilealchemist."""
    if sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Caches/{CACHE_NAME}")
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LOCALAPPDATA")
                            or os.path.expanduser("~/AppData/Local"),
                            CACHE_NAME, "Cache")
    xdg_cache_home: str = os.environ.get("XDG_CACHE_HOME", "")
    if not os.path.isabs(xdg_cache_home):
        xdg_cache_home = os.path.expanduser("~/.cache")
    return os.path.join(xdg_cache_home, CACHE_NAME)


def _install(path: str) -> None:
    """Downloads, checks and unpacks the release to `path`, atomically.

    Raises:
        RuntimeError: If no release is pinned for this platform, or the
            download doesn't match its hash.
        requests.HTTPError: If the download fails.
    """
    asset: str
    expected: str
    asset, expected = _release_asset()
    print(f"downloading go-pmtiles {VERSION} ({asset}) into {path}",
          file=sys.stderr)
    response: requests.Response = requests.get(f"{RELEASE_URL}/{asset}",
                                               timeout=60)
    response.raise_for_status()
    digest: str = hashlib.sha256(response.content).hexdigest()
    if digest != expected:
        raise RuntimeError(f"{asset} has SHA-256 {digest}, not the pinned "
                           f"{expected}; refusing to run it")
    binary: bytes = _extract(asset, response.content, os.path.basename(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary: str = f"{path}.{os.getpid()}.tmp"
    handle: BinaryIO
    with open(temporary, "wb") as handle:
        handle.write(binary)
    os.chmod(temporary, os.stat(temporary).st_mode | stat.S_IXUSR)
    os.replace(temporary, path)


def _release_asset() -> tuple[str, str]:
    """Returns this platform's asset name and SHA-256.

    Raises:
        RuntimeError: If no release is pinned for this platform.
    """
    system: str = platform.system()
    machine: str = platform.machine().lower()
    machine = MACHINE_ALIASES.get(machine, machine)
    if (system, machine) not in ASSETS:
        raise RuntimeError(f"no go-pmtiles {VERSION} release is pinned for "
                           f"{system} {machine}; install `pmtiles` yourself "
                           f"and point {OVERRIDE_VARIABLE} at it")
    return ASSETS[system, machine]


def _extract(asset: str, content: bytes, member: str) -> bytes:
    """Returns `member` from the zip or tar.gz archive `content`.

    Raises:
        RuntimeError: If `member` is not a regular file.
    """
    zip_archive: zipfile.ZipFile
    if asset.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(content)) as zip_archive:
            return zip_archive.read(member)
    tar_archive: tarfile.TarFile
    with tarfile.open(fileobj=io.BytesIO(content)) as tar_archive:
        extracted: IO[bytes] | None = tar_archive.extractfile(member)
        if extracted is None:
            raise RuntimeError(f"{member} in {asset} is not a regular file")
        return extracted.read()
