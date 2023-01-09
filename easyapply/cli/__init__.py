import logging
import os
import shutil
import tempfile
from pathlib import Path

import typer
import yaml

from .. import pdf, themes

app = typer.Typer()


def init_logging():
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())


@app.command()
def list_themes():
    print("List of themes")


@app.command()
def build(
    output: Path = Path.cwd() / "cv.pdf",
    input: Path = Path.cwd() / "application.yaml",
    debug: bool = False,
):
    input = input.resolve()
    output = output.resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        with open(input) as fptr:
            config = yaml.safe_load(fptr)

        template = themes.load_template(config["theme"]["name"])

        build_pdf = output.suffix == ".pdf"

        html_path = tmppath / "cv.html"
        html_path.write_text(
            template.render(
                theme=config["theme"],
                cv=config["cv"],
                theme_dir=Path(template.filename).parent.parent,
                build_pdf=build_pdf,
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
