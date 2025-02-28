import logging
import urllib.parse
import urllib.request
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def read_text(origin: Path | str) -> str:
    """
    Reads the contents of a file at the given path as text.

    Parameters:
        origin (Path | str): the path to the file to read

    Returns:
        str: the contents of the file

    If the path is remote (i.e. starts with "http://"), uses :external+python:py:func:`urllib.request.urlopen` to read the file.
    Otherwise, uses :external+python:py:meth:`pathlib.Path.read_text`.
    """
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        LOGGER.debug(f"Loading remote resource (text): {origin}")
        with urllib.request.urlopen(origin) as req:
            return req.read().decode()

    LOGGER.debug(f"Loading local resource: {origin}")
    if scheme == "file":
        return Path(urllib.parse.urlparse(origin).path).read_text()

    return Path(origin).read_text()


def read_bytes(origin: Path | str) -> bytes:
    """
    Reads the contents of a file at the given path as bytes.

    Parameters:
        origin (Path | str): the path to the file to read

    Returns:
        bytes: the contents of the file

    If the path is remote (i.e. starts with "http://"), uses :external+python:py:func:`urllib.request.urlopen` to read the file.
    Otherwise, uses :external+python:py:meth:`pathlib.Path.read_bytes`.
    """
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        LOGGER.debug(f"Loading remote resource (binary): {origin}")
        with urllib.request.urlopen(origin) as req:
            return req.read()

    LOGGER.debug(f"Loading local resource (binary): {origin}")
    if scheme == "file":
        return Path(urllib.parse.urlparse(origin).path).read_bytes()

    return Path(origin).read_bytes()
