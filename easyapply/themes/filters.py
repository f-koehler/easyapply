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

# TODO(fk): do not register globally
ElementTree.register_namespace("", "http://www.w3.org/2000/svg")


LOGGER = logging.getLogger(__name__)

RE_URL_PROTO = re.compile(r"^\w+://(.+)")
RE_GITHUB_USERNAME = re.compile(r"^github\.com/([\w\d\-]+)(?:$|/.*)")


def strip_url_protocol(url: str) -> str:
    """
    Remove the protocol part from a URL, if present.

    Args:
        url (str): The URL to strip the protocol from.

    Returns:
        str: The URL without the protocol part.

    Raises:
        ValueError: If the URL is invalid.
    """
    m = RE_URL_PROTO.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid URL: {url}")


def get_github_username(url: str) -> str:
    """
    Extract the GitHub username from a given GitHub URL.

    Args:
        url (str): The GitHub URL from which to extract the username.

    Returns:
        str: The GitHub username.

    Raises:
        ValueError: If the URL is invalid or does not contain a valid GitHub username.
    """

    url = strip_url_protocol(url)
    m = RE_GITHUB_USERNAME.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid GitHub URL: {url}")


def parse_date(date: str) -> datetime.datetime:
    """
    Parse a date string into a datetime object.

    The string should be in one of the following formats: "%Y-%m-%d", "%Y-%m", "%Y".

    Args:
        date (str): The date string to parse.

    Returns:
        datetime.datetime: The parsed datetime object.

    Raises:
        ValueError: If the date string is invalid.
    """
    if len(date) == 10:
        return datetime.datetime.strptime(date, "%Y-%m-%d")

    if len(date) == 7:
        return datetime.datetime.strptime(date, "%Y-%m")

    if len(date) == 4:
        return datetime.datetime.strptime(date, "%Y")

    raise ValueError(f"Invalid date: {date}")


def format_date(date: datetime.datetime, format: str) -> str:
    """
    Format a datetime object into a string using the given format.

    Args:
        date (datetime.datetime): The datetime object to format.
        format (str): The format string to use, as accepted by the datetime.strftime() method.

    Returns:
        str: The formatted string.
    """
    return date.strftime(format)


def day_suffix(date: datetime.datetime) -> str:
    """
    Return the day suffix of the given date.

    The day suffix is a string, one of "st", "nd", "rd", or "th".

    The rule for determining the day suffix is as follows:
    - If the day is between 4 and 20 (inclusive), or between 24 and 30 (inclusive), the day suffix is "th".
    - Otherwise, the day suffix is determined by the last digit of the day:
        - If the day ends with 1, the day suffix is "st".
        - If the day ends with 2, the day suffix is "nd".
        - If the day ends with 3, the day suffix is "rd".

    Args:
        date (datetime.datetime): The date to get the day suffix for.

    Returns:
        str: The day suffix of the given date.
    """
    if (4 <= date.day <= 20) or (24 <= date.day <= 30):
        return "th"
    return ["st", "nd", "rd"][date.day % 10 - 1]


@functools.cache
def find_scour() -> tuple[bool, Path | None]:
    """
    Locate the 'scour' command-line tool in the system's PATH.

    This function checks if the 'scour' tool, used for optimizing SVG files, is available
    on the system by searching for it in the system's PATH. The result is cached to avoid
    repeated checks.

    Returns:
        tuple[bool, Path | None]: A tuple where the first element is a boolean indicating
        whether 'scour' was found, and the second element is the Path to the 'scour' executable
        if found, otherwise None.
    """

    path = shutil.which("scour")
    if not path:
        LOGGER.error("Could not find scour, skipping SVG optimization")
        return False, None
    LOGGER.info(f"Found scour: {path}")
    return True, Path(path)


@functools.cache
def find_svgo() -> tuple[bool, Path | None]:
    """
    Locate the 'svgo' command-line tool in the system's PATH.

    This function checks if the 'svgo' tool, used for optimizing SVG files, is available
    on the system by searching for it in the system's PATH. The result is cached to avoid
    repeated checks.

    Returns:
        tuple[bool, Path | None]: A tuple where the first element is a boolean indicating
        whether 'svgo' was found, and the second element is the Path to the 'svgo' executable
        if found, otherwise None.
    """

    path = shutil.which("svgo")
    if not path:
        LOGGER.error("Could not find svgo, skipping SVG optimization")
        return False, None
    LOGGER.info(f"Found svgo: {path}")
    return True, Path(path)


def set_fill(svg: str, color: str) -> str:
    """
    Set the fill color of all paths in the given SVG string to the specified color.

    Args:
        svg (str): The SVG string to modify.
        color (str): The color to set as the fill color of all paths.

    Returns:
        str: The modified SVG string with the fill color set.
    """
    parsed = ElementTree.fromstring(svg)
    for element in parsed.iter("{http://www.w3.org/2000/svg}path"):
        element.attrib["fill"] = color
    return ElementTree.tostring(parsed).decode()


def set_stroke(svg: str, color: str) -> str:
    """
    Set the stroke color of all paths in the given SVG string to the specified color.

    Args:
        svg (str): The SVG string to modify.
        color (str): The color to set as the stroke color of all paths.

    Returns:
        str: The modified SVG string with the stroke color set.
    """

    parsed = ElementTree.fromstring(svg)
    for element in parsed.iter("{http://www.w3.org/2000/svg}path"):
        element.attrib["stroke"] = color
    return ElementTree.tostring(parsed).decode()


def svgo(svg: str) -> str:
    """
    Optimize the given SVG string using the `svgo` command-line tool.

    If the `svgo` tool is not found in the system's PATH, the input SVG string is returned unmodified.

    The optimized SVG string is cached to avoid repeated optimization of the same SVG string. The cache
    is stored in the `easyapply-cache/svgo` directory in the system's temporary directory.

    Args:
        svg (str): The SVG string to optimize.

    Returns:
        str: The optimized SVG string.
    """
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
    """
    Optimize the given SVG string using the `scour` command-line tool.

    If the `scour` tool is not found in the system's PATH, the input SVG string is returned unmodified.

    The optimized SVG string is cached to avoid repeated optimization of the same SVG string. The cache
    is stored in the `easyapply-cache/scour` directory in the system's temporary directory.

    Args:
        svg (str): The SVG string to optimize.

    Returns:
        str: The optimized SVG string.
    """
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
    """
    Embed a JavaScript code block into an HTML string.

    Args:
        code (str): The JavaScript code block to embed.

    Returns:
        str: An HTML string containing the embedded JavaScript code block.
    """
    return f"<script type='text/javascript'>{code}</script>"


def bibtex(source: str) -> str:
    """
    Convert a BibTeX source string into an HTML bibliography.

    This function parses a given BibTeX source string, formats the parsed
    data into a bibliography using a specified style, and converts it to
    HTML format. The HTML content is then extracted and returned as a string.

    Args:
        source (str): A string containing BibTeX entries.

    Returns:
        str: An HTML string representing the formatted bibliography.
    """

    publications = pybtex.database.input.bibtex.Parser().parse_string(source)
    style: pybtex.style.formatting.BaseStyle = pybtex.plugin.find_plugin(
        "pybtex.style.formatting",
        "plain",
    )(
        label_style="number",
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
    """
    Encode given byte data in Base64 and return as a string.

    Args:
        data (bytes): The bytes data to encode.

    Returns:
        str: The Base64 encoded string.
    """
    return base64.b64encode(data).decode()


def embed_image(img: str, extension: str = "png", **attributes: str) -> str:
    """
    Embed the given image data into an HTML <img> string.

    Args:
        img (str): The Base64 encoded image data.
        extension (str, optional): The file extension of the image. Defaults to "png".
        **attributes (str): Additional attributes to add to the <img> tag.

    Returns:
        str: An HTML string containing the embedded image.
    """
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
    """
    Add given attributes to the SVG string.

    Args:
        svg (str): The SVG string.
        **attributes (str): Additional attributes to add to the SVG tag.

    Returns:
        str: The modified SVG string with the added attributes.
    """
    if "class_" in attributes:
        if "class" in attributes:
            raise ValueError("Cannot set both _class and class")
        attributes["class"] = attributes["class_"]
        del attributes["class_"]

    parsed = ElementTree.fromstring(svg)
    parsed.attrib.update(attributes)
    return ElementTree.tostring(parsed).decode()


def href_phone(phone: str) -> str:
    """
    Convert a phone number into a 'tel:' URI.

    Args:
        phone (str): The phone number to convert.

    Returns:
        str: The 'tel:' URI for the given phone number.

    Notes:
        This function removes all non-digit characters from the given phone
        number and prefixes it with 'tel:' to create a valid 'tel:' URI.
    """
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")
    return "tel:" + phone


def href_email(email: str) -> str:
    """
    Convert an email address into a 'mailto:' URI.

    Args:
        email (str): The email address to convert.

    Returns:
        str: The 'mailto:' URI for the given email address.
    """

    return "mailto:" + email


def rasterize(svg: str, dpi: int = 300) -> bytes:
    """
    Convert an SVG string into a rasterized PNG image.

    Args:
        svg (str): The SVG string to convert.
        dpi (int, optional): The DPI of the output image. Defaults to 300.

    Returns:
        bytes: The PNG image as bytes.
    """
    return cairosvg.svg2png(bytestring=svg.encode(), dpi=dpi)


def split_paragraphs(text: str) -> list[str]:
    """
    Split a given text into paragraphs.

    Args:
        text (str): The text to split into paragraphs.

    Returns:
        list[str]: A list of strings, where each string is a paragraph.

    Notes:
        This function splits the given text on double line breaks to create
        paragraphs. It does not perform any additional processing on the text.
    """
    return text.split("\n\n")
