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
    env.filters["set_fill"] = filters.set_fill
    env.filters["set_stroke"] = filters.set_stroke
    env.filters["svgo"] = filters.svgo
    env.filters["scour"] = filters.scour
    env.filters["scour"] = filters.add_attributes
    env.filters["add_attributes"] = filters.add_attributes

    env.globals["read_text"] = globals.read_text
    env.globals["embed_js"] = globals.embed_js
    env.globals["embed_image_base64"] = globals.embed_image_base64
    env.globals["render_bibfile"] = globals.render_bibfile
    return env


def load_template(name: str, template: str = "cv.html") -> jinja2.Template:
    template_dir = Path.cwd().parent / "themes" / name / "templates"
    env = get_env(template_dir)
    return env.get_template(template)
