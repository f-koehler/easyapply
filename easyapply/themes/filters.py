import base64
import datetime
import functools
import hashlib
import io
import logging
import mimetypes
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import bs4
import cairosvg
import pybtex.backends.html
import pybtex.database
import pybtex.database.input.bibtex
import pybtex.plugin
import pybtex.style.formatting

ElementTree.register_namespace("", "http://www.w3.org/2000/svg")


LOGGER = logging.getLogger(__name__)

RE_URL_PROTO = re.compile(r"^\w+://(.+)")
RE_GITHUB_USERNAME = re.compile(r"^github\.com/([\w\d\-]+)(?:$|/.*)")


def strip_url_protocol(url: str) -> str:
    m = RE_URL_PROTO.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid URL: {url}")


def get_github_username(url: str) -> str:
    url = strip_url_protocol(url)
    m = RE_GITHUB_USERNAME.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid GitHub URL: {url}")


def parse_date(date: str) -> datetime.datetime:
    if len(date) == 10:
        return datetime.datetime.strptime(date, "%Y-%m-%d")

    if len(date) == 7:
        return datetime.datetime.strptime(date, "%Y-%m")

    if len(date) == 4:
        return datetime.datetime.strptime(date, "%Y")

    raise ValueError(f"Invalid date: {date}")


def format_date(date: datetime.datetime, format: str) -> str:
    return date.strftime(format)


def day_suffix(date: datetime.datetime) -> str:
    if (4 <= date.day <= 20) or (24 <= date.day <= 30):
        return "th"
    return ["st", "nd", "rd"][date.day % 10 - 1]


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


def set_fill(svg: str, color: str) -> str:
    parsed = ElementTree.fromstring(svg)
    for element in parsed.iter("{http://www.w3.org/2000/svg}path"):
        element.attrib["fill"] = color
    return ElementTree.tostring(parsed).decode()


def set_stroke(svg: str, color: str) -> str:
    parsed = ElementTree.fromstring(svg)
    for element in parsed.iter("{http://www.w3.org/2000/svg}path"):
        element.attrib["stroke"] = color
    return ElementTree.tostring(parsed).decode()


def svgo(svg: str) -> str:
    svgo_found, svgo_path = find_svgo()
    if not svgo_found:
        LOGGER.error("Cannot apply svgo as command was not found")
        return svg

    hash = hashlib.sha256(svg.encode()).hexdigest()
    cache_dir = Path(tempfile.gettempdir()) / "easyapply-cache" / "svgo"
    cache_file = cache_dir / (hash + ".svg")
    if cache_file.exists():
        return cache_file.read_text()

    cache_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(svgo_path),
        "--input",
        "-",
        "--output",
        "-",
        "--multipass",
    ]
    optimized = subprocess.check_output(cmd, input=svg.encode()).decode()
    cache_file.write_text(optimized)
    return optimized


def scour(svg: str) -> str:
    scour_found, scour_path = find_scour()
    if not scour_found:
        LOGGER.error("Cannot apply scour as command was not found")
        return svg

    hash = hashlib.sha256(svg.encode()).hexdigest()
    cache_dir = Path(tempfile.gettempdir()) / "easyapply-cache" / "scour"
    cache_file = cache_dir / (hash + ".svg")
    if cache_file.exists():
        return cache_file.read_text()

    cache_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(scour_path),
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
    optimized = subprocess.check_output(cmd, input=svg.encode()).decode()
    cache_file.write_text(optimized)
    return optimized


def embed_js(code: str) -> str:
    return f"<script type='text/javascript'>{code}</script>"


def bibtex(source: str) -> str:
    publications = pybtex.database.input.bibtex.Parser().parse_string(source)
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

    soup = bs4.BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    return "".join(str(x) for x in body.contents)


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode()


def embed_image(img: str, extension: str = "png", **attributes: str) -> str:
    if "class_" in attributes:
        if "class" in attributes:
            raise ValueError("Cannot set both _class and class")
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    mimetype, _ = mimetypes.guess_type("test." + extension)

    if mimetype is None:
        raise ValueError(f"Could not guess mimetype for .{extension}")

    attrs = " ".join(f'{key}="{attributes[key]}"' for key in attributes)

    return f"<img {attrs} src='data:{mimetype};base64,{img}'>"


def add_attributes(svg: str, **attributes: str) -> str:
    if "class_" in attributes:
        if "class" in attributes:
            raise ValueError("Cannot set both _class and class")
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    parsed = ElementTree.fromstring(svg)
    parsed.attrib.update(attributes)
    return ElementTree.tostring(parsed).decode()


def href_phone(phone: str) -> str:
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")
    return "tel:" + phone


def href_email(email: str) -> str:
    return "mailto:" + email


def rasterize(svg: str, dpi: int = 300) -> bytes:
    return cairosvg.svg2png(bytestring=svg.encode(), dpi=dpi)
