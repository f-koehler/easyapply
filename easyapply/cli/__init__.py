import logging
import os
import shutil
import tempfile
from pathlib import Path

import typer
import yaml

from .. import pdf
from .. import themes

app = typer.Typer(help="easyapply job application generator")


def init_logging():
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())


@app.command()
def list_themes():
    print("List of themes")


RESERVED_KEYS = [
    "theme_dir",
    "build_pdf",
]


@app.command()
def build(
    output: Path = typer.Option(
        Path("cv.pdf"),
        help="Path to the output file.",
    ),
    input: Path = typer.Option(
        Path("application.yaml"),
        help="Path to the input YAML file.",
    ),
    debug: bool = typer.Option(
        False,
        help="Save the intermediary HTML for PDF generation.",
    ),
):
    input = input.resolve()
    output = output.resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        with open(input) as fptr:
            config = yaml.safe_load(fptr)

        for reserved in RESERVED_KEYS:
            if reserved in config:
                raise ValueError("Reserved key in config: {reserved}")

        template = themes.load_template(config["theme"]["name"])

        build_pdf = output.suffix == ".pdf"

        html_path = tmppath / "cv.html"
        html_path.write_text(
            template.render(
                theme_dir=Path(template.filename).parent.parent,
                build_pdf=build_pdf,
                **config,
            ),
        )

        if build_pdf:
            pdf_path = tmppath / "cv.pdf"
            pdf.render_file(html_path, pdf_path)
            shutil.copy2(pdf_path, output)

            if debug:
                shutil.copy2(html_path, output.with_suffix(".pdf.html"))
        else:
            shutil.copy2(html_path, output)


def main():
    init_logging()
    app()


if __name__ == "__main__":
    main()
