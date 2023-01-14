import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import typer
import yaml

from .. import pdf
from .. import themes

app = typer.Typer(help="easyapply job application generator")


def init_logging():
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())


LOGGER = logging.getLogger(__name__)
RESERVED_KEYS = [
    "theme_dir",
    "build_pdf",
]


def check_config(config: dict[str, Any]):
    for reserved in RESERVED_KEYS:
        if reserved in config:
            raise ValueError("Reserved key in config: {reserved}")

    if "theme" not in config:
        raise ValueError("Missing theme setting config")

    if "name" not in config["theme"]:
        raise ValueError("Missing name setting in confg['theme']")


@app.command()
def render(
    name: Path = typer.Argument(
        ...,
        help="Relative of the template within the theme.",
    ),
    input: Path = typer.Option(
        Path("application.yaml"),
        "--input",
        "-i",
        help="Path to the input YAML file.",
    ),
):
    input = input.resolve()

    with open(input, "r") as fptr:
        config = yaml.safe_load(fptr)

    check_config(config)

    template = themes.load_template(
        config["theme"]["name"],
        template=str(name),
    )
    rendered = template.render(
        theme_dir=Path(template.filename).parent.parent,
        build_pdf=False,
        **config,
    )
    print(rendered)


@app.command()
def build(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to build.",
    ),
    build_pdf: bool = typer.Option(
        False,
        "--pdf",
        help="Build PDFs",
    ),
    debug_pdf: bool = typer.Option(
        False,
        help="Save the intermediary HTML used for PDF generation.",
    ),
):
    directory = directory.resolve()

    for name in ["application.yaml", "application.yml"]:
        if (path := directory / name).exists():
            config_path = path
            break
    else:
        raise FileNotFoundError(
            f"application.yaml/application.yml not found in directory: {directory}"
        )

    with open(config_path, "r") as fptr:
        config = yaml.safe_load(fptr)

    check_config(config)

    for template_file in config["theme"]["templates"]:
        LOGGER.info("Rendering template %s", template_file)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            template = themes.load_template(
                config["theme"]["name"],
                template=template_file,
            )

            html_path = tmppath / "output.html"
            html_path.write_text(
                template.render(
                    theme_dir=Path(template.filename).parent.parent,
                    build_pdf=build_pdf,
                    **config,
                ),
            )

            if build_pdf:
                pdf_path = tmppath / "output.pdf"
                pdf.render_file(html_path, pdf_path)
                shutil.copy2(pdf_path, (directory / template_file).with_suffix(".pdf"))

                if debug_pdf:
                    shutil.copy2(
                        html_path, (directory / template_file).with_suffix(".pdf.html")
                    )
            else:
                shutil.copy2(html_path, directory / template_file)


def main():
    init_logging()
    app()


if __name__ == "__main__":
    main()
