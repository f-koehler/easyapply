import base64
import io
import mimetypes
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


def read_text_file(origin: Path | str) -> str:
    if isinstance(origin, Path):
        origin = str(origin.resolve())

    scheme = urllib.parse.urlparse(origin).scheme

    if scheme in ("http", "https"):
        with urllib.request.urlopen(origin) as fptr:
            return fptr.read().decode()

    if scheme == "file":
        Path(urllib.parse.urlparse(origin).path).read_text()

    return Path(origin).read_text()


def embed_js_base64(origin: Path | str) -> str:
    code = read_text_file(origin)
    encoded = base64.standard_b64encode(code.encode()).decode()
    return f"<script src='data:text/javascript;base64,{encoded}'></script>"


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

    return f"<img {attrs} src='data:{mimetype};base64,{encoded}'/>"


def embed_svg(path: Path, **attributes: str) -> str:
    if "class_" in attributes:
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    with open(path) as fptr:
        svg = ElementTree.fromstring(fptr.read())

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
