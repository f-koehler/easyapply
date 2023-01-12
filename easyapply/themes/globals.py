import logging
import urllib.parse
import urllib.request
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def read_text(origin: Path | str) -> str:
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        LOGGER.info(f"Loading remote resource (text): {origin}")
        with urllib.request.urlopen(origin) as req:
            return req.read().decode()

    LOGGER.info(f"Loading local resource: {origin}")
    if scheme == "file":
        return Path(urllib.parse.urlparse(origin).path).read_text()

    return Path(origin).read_text()


def read_bytes(origin: Path | str) -> bytes:
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        LOGGER.info(f"Loading remote resource (binary): {origin}")
        with urllib.request.urlopen(origin) as req:
            return req.read()

    LOGGER.info(f"Loading local resource (binary): {origin}")
    if scheme == "file":
        return Path(urllib.parse.urlparse(origin).path).read_bytes()

    return Path(origin).read_bytes()
