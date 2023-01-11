import base64
import functools
import hashlib
import io
import logging
import mimetypes
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

import pybtex.backends.html
import pybtex.database
import pybtex.database.input.bibtex
import pybtex.plugin
import pybtex.style.formatting

ElementTree.register_namespace("", "http://www.w3.org/2000/svg")

LOGGER = logging.getLogger(__name__)


def read_text_file(origin: Path | str) -> str:
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        LOGGER.info(f"Loading remote resource: {origin}")
        with urllib.request.urlopen(origin) as req:
            return req.read().decode()

    LOGGER.info(f"Loading local resource: {origin}")
    if scheme == "file":
        return Path(urllib.parse.urlparse(origin).path).read_text()

    return Path(origin).read_text()


def embed_js(origin: Path | str) -> str:
    LOGGER.info(f"Embedding JS: {origin}")
    code = read_text_file(origin)
    return f"<script type='text/javascript'>{code}</script>"


def embed_image_base64(path: Path, **attributes: dict[str, str]) -> str:
    if "class_" in attributes:
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    mimetype, _ = mimetypes.guess_type(path)
    with open(path, "rb") as fptr:
        encoded = base64.standard_b64encode(fptr.read()).decode()

    if mimetype is None:
        raise ValueError(f"Could not guess mimetype for {path}")

    attrs = " ".join(f'{key}="{attributes[key]}"' for key in attributes)
    if attrs:
        attrs = " " + attrs

    return f"<img {attrs} src='data:{mimetype};base64,{encoded}'>"


@functools.cache
def find_scour() -> tuple[bool, Path | None]:
    path = shutil.which("scour")
    if not path:
        LOGGER.error("Could not find scour, skipping SVG optimization")
        return False, None
    LOGGER.info(f"Found scour: {path}")
    return True, Path(path)


@functools.cache
def find_svgo() -> tuple[bool, Path | None]:
    path = shutil.which("svgo")
    if not path:
        LOGGER.error("Could not find svgo, skipping SVG optimization")
        return False, None
    LOGGER.info(f"Found svgo: {path}")
    return True, Path(path)


def optimize_svg(svg: str) -> str:
    scour_found, scour_path = find_scour()
    svgo_found, svgo_path = find_svgo()

    suffix = ""
    suffix += "_svgo" if svgo_found else ""
    suffix += "_scour" if scour_found else ""
    cachedir = Path(tempfile.gettempdir()) / ("easyapply_svg_cache" + suffix)
    cachedir.mkdir(parents=True, exist_ok=True)

    hash = hashlib.sha256(svg.encode()).hexdigest()
    cachefile = cachedir / f"{hash}.svg"
    if cachefile.exists():
        return cachefile.read_text()

    if svgo_found:
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.svg"
            optimized = Path(tmpdir) / "optimized.svg"
            original.write_text(svg)

            cmd = [
                str(svgo_path),
                "--input",
                str(original),
                "--output",
                str(optimized),
                "--multipass",
            ]
            subprocess.check_output(cmd)
            svg = optimized.read_text()

    if scour_found:
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.svg"
            optimized = Path(tmpdir) / "optimized.svg"
            original.write_text(svg)

            cmd = [
                str(scour_path),
                "-i",
                str(original),
                "-o",
                str(optimized),
                "--set-precision=8",
                "--enable-id-stripping",
                "--shorten-ids",
                "--create-groups",
                "--renderer-workaround",
                "--strip-xml-prolog",
                "--remove-titles",
                "--remove-descriptions",
                "--enable-viewboxing",
                "--strip-xml-space",
                "--no-line-breaks",
            ]
            subprocess.check_output(cmd)
            svg = optimized.read_text()

    cachefile.write_text(svg)

    return svg


def embed_svg(origin: str | Path, **attributes: str) -> str:
    if "class_" in attributes:
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    svg = ElementTree.fromstring(optimize_svg(read_text_file(origin)))
    svg.attrib.update(attributes)
    return ElementTree.tostring(svg).decode()


def render_bibfile(bibfile: str | Path) -> str:
    bibfile = Path(str(bibfile)).resolve()
    if not bibfile.exists():
        raise FileNotFoundError(f"Could not find {bibfile}")

    bibfile = str(bibfile)
    publications = pybtex.database.input.bibtex.Parser().parse_file(bibfile)
    style: pybtex.style.formatting.BaseStyle = pybtex.plugin.find_plugin(
        "pybtex.style.formatting",
        "plain",
    )(
        label_style="number",
        sorting_style="none",
        name_style="plain",
        abbreviate_names=True,
    )
    formatted = style.format_bibliography(publications)
    backend = pybtex.backends.html.Backend()
    html = backend.write_to_file(formatted, io.StringIO())
    return html
