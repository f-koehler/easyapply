import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
import contextlib

from rich.logging import RichHandler
import typer
import watchdog.events
import watchdog.observers
import yaml

from .. import pdf, themes

app = typer.Typer(help="easyapply job application generator")


@contextlib.contextmanager
def change_working_directory(directory: Path):
    current_cwd = Path.cwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(current_cwd)


def init_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "INFO"),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )


LOGGER = logging.getLogger(__name__)
RESERVED_KEYS = [
    "theme_dir",
    "build_pdf",
]


def check_config(config: dict[str, Any]) -> None:
    for reserved in RESERVED_KEYS:
        if reserved in config:
            raise ValueError("Reserved key in config: {reserved}")

    if "theme" not in config:
        raise ValueError("Missing theme setting config")

    if "name" not in config["theme"]:
        raise ValueError("Missing name setting in confg['theme']")


def load_config(directory: Path) -> dict[str, Any]:
    for name in ["application.yaml", "application.yml"]:
        if (config_path := directory / name).exists():
            with open(config_path) as fptr:
                config = yaml.safe_load(fptr)
                check_config(config)
                return config
    else:
        raise FileNotFoundError(
            f"application.yaml/application.yml not found in directory: {directory}"
        )


@app.command(help="Render a specific template.")
def render(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to build.",
    ),
    name: Path = typer.Argument(..., help="Relative of the template within the theme."),
) -> None:
    with change_working_directory(directory):
        config = load_config(Path.cwd())

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


@app.command(help="Build application project.")
def build(
    directory: Path = typer.Argument(Path("."), help="Directory to build."),
    output_directory: Path | None = typer.Option(
        None,
        "-o",
        "--output",
        help="Directory to save output files, defaults to build directory.",
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
) -> None:
    if output_directory:
        output_directory = output_directory.resolve()
    else:
        output_directory = Path.cwd().resolve()
    with change_working_directory(directory):
        config = load_config(Path.cwd())

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
                    pdf_out_path = (output_directory / template_file).with_suffix(
                        ".pdf"
                    )
                    pdf.render_file(html_path, pdf_path)
                    shutil.copy2(pdf_path, pdf_out_path)

                    if debug_pdf:
                        shutil.copy2(
                            html_path,
                            (output_directory / template_file).with_suffix(".pdf.html"),
                        )
                else:
                    shutil.copy2(html_path, output_directory / template_file)


class BuildEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(
        self, directory: Path, build_pdf: bool = False, debug_pdf: bool = False
    ) -> None:
        self.directory = directory
        self.build_pdf = build_pdf
        self.debug_pdf = debug_pdf

    def on_any_event(self, event: watchdog.events.FileSystemEvent) -> None:
        build(self.directory, build_pdf=self.build_pdf, debug_pdf=self.debug_pdf)


@app.command(help="Build application project and watch for changes.")
def watch(
    directory: Path = typer.Argument(Path("."), help="Directory to build."),
    build_pdf: bool = typer.Option(
        False,
        "--pdf",
        help="Build PDFs",
    ),
    debug_pdf: bool = typer.Option(
        False,
        help="Save the intermediary HTML used for PDF generation.",
    ),
) -> None:
    with change_working_directory(directory):
        build(Path.cwd(), build_pdf=build_pdf, debug_pdf=debug_pdf)

        config = load_config(Path.cwd())
        theme_dir = themes.find_theme(config["theme"]["name"])

        event_handler = BuildEventHandler(Path.cwd())
        observer = watchdog.observers.Observer()
        observer.schedule(
            event_handler, Path.cwd() / "application.yaml", recursive=True
        )
        observer.schedule(event_handler, theme_dir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def main() -> None:
    init_logging()
    app()


if __name__ == "__main__":
    main()
