import functools
from pathlib import Path

import jinja2

from . import filters, globals


@functools.cache
def get_env(directory: Path) -> jinja2.Environment:
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
    env.filters["scour"] = filters.add_attributes
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
    template_dir = Path.cwd() / "themes" / name

    if template_dir.exists():
        return template_dir

    template_dir = Path.cwd().parent / "themes" / name
    if template_dir.exists():
        return template_dir

    return None


def load_template(name: str, template: str) -> jinja2.Template:
    if theme_dir := find_theme(name):
        return get_env(theme_dir / "templates").get_template(template)
    raise RuntimeError(f"Theme {name} not found")
