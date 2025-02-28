import functools
from pathlib import Path

import jinja2

from . import filters, globals


@functools.cache
def get_env(directory: Path) -> jinja2.Environment:
    """
    Return a cached Jinja2 Environment for the given directory.

    Parameters:
        directory (Path): The directory to load templates from.

    Returns:
        jinja2.Environment: The cached Jinja2 Environment.

    Filters:
      - :py:func:`~easyapply.themes.filters.strip_url_protocol`
      - :py:func:`~easyapply.themes.filters.parse_date`
      - :py:func:`~easyapply.themes.filters.format_date`
      - :py:func:`~easyapply.themes.filters.day_suffix`
      - :py:func:`~easyapply.themes.filters.set_fill`
      - :py:func:`~easyapply.themes.filters.set_stroke`
      - :py:func:`~easyapply.themes.filters.svgo`
      - :py:func:`~easyapply.themes.filters.scour`
      - :py:func:`~easyapply.themes.filters.add_attributes`
      - :py:func:`~easyapply.themes.filters.embed_js`
      - :py:func:`~easyapply.themes.filters.bibtex`
      - :py:func:`~easyapply.themes.filters.embed_image`
      - :py:func:`~easyapply.themes.filters.b64encode`
      - :py:func:`~easyapply.themes.filters.href_phone`
      - :py:func:`~easyapply.themes.filters.href_email`
      - :py:func:`~easyapply.themes.filters.rasterize`
      - :py:func:`~easyapply.themes.filters.split_paragraphs`

    Globals:
      - :py:func:`~easyapply.themes.globals.read_text`
      - :py:func:`~easyapply.themes.globals.read_bytes`
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        bytecode_cache=jinja2.FileSystemBytecodeCache(),
    )
    env.filters["strip_url_protocol"] = filters.strip_url_protocol
    env.filters["parse_date"] = filters.parse_date
    env.filters["format_date"] = filters.format_date
    env.filters["day_suffix"] = filters.day_suffix
    env.filters["set_fill"] = filters.set_fill
    env.filters["set_stroke"] = filters.set_stroke
    env.filters["svgo"] = filters.svgo
    env.filters["scour"] = filters.scour
    env.filters["add_attributes"] = filters.add_attributes
    env.filters["embed_js"] = filters.embed_js
    env.filters["bibtex"] = filters.bibtex
    env.filters["embed_image"] = filters.embed_image
    env.filters["b64encode"] = filters.b64encode
    env.filters["href_phone"] = filters.href_phone
    env.filters["href_email"] = filters.href_email
    env.filters["rasterize"] = filters.rasterize
    env.filters["split_paragraphs"] = filters.split_paragraphs

    env.globals["read_text"] = globals.read_text
    env.globals["read_bytes"] = globals.read_bytes
    return env


def find_theme(name: str) -> Path | None:
    """
    Return the path to the theme directory with the given name.

    The function first checks if a theme with the given name is in the current working directory.
    If it is, it returns the path to that directory.
    If not, it checks if a theme with the given name is in the parent directory of the current working directory.
    If it is, it returns the path to that directory.
    If not, it returns None.

    Parameters:
        name (str): The name of the theme to find.

    Returns:
        Path | None: The path to the theme directory, or None if the theme was not found.
    """
    template_dir = Path.cwd() / "themes" / name

    if template_dir.exists():
        return template_dir

    template_dir = Path.cwd().parent / "themes" / name
    if template_dir.exists():
        return template_dir

    return None


def load_template(name: str, template: str) -> jinja2.Template:
    """
    Return a Jinja2 template from the given theme.

    The function first checks if a theme with the given name is in the current working directory.
    If it is, it returns a Jinja2 template from the theme's "templates" directory with the given name.
    If not, it checks if a theme with the given name is in the parent directory of the current working directory.
    If it is, it returns a Jinja2 template from the theme's "templates" directory with the given name.
    If not, it raises a RuntimeError.

    Parameters:
        name (str): The name of the theme to load the template from.
        template (str): The name of the template to load from the theme.

    Returns:
        jinja2.Template: The loaded Jinja2 template.

    Raises:
        RuntimeError: If the theme with the given name was not found.
    """
    if theme_dir := find_theme(name):
        return get_env(theme_dir / "templates").get_template(template)
    raise RuntimeError(f"Theme {name} not found")
