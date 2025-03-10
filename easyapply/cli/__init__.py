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
    """
    A context manager that temporarily changes the current working directory
    to the specified directory.

    Parameters:
    directory (Path): The target directory to change to temporarily.

    Yields:
    None: Temporarily changes the working directory to the specified path
    and reverts back to the original directory after the context exits.
    """

    current_cwd = Path.cwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(current_cwd)


def init_logging() -> None:
    """
    Initialize the logging system.

    The logging level is determined by the LOGLEVEL environment variable, which
    can be set to one of the following values:

        - CRITICAL
        - ERROR
        - WARNING
        - INFO
        - DEBUG
        - NOTSET

    The default value is INFO.

    The output format is set to plain text with a timestamp.

    The logging is configured to use the RichHandler which provides colored
    output.
    """
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
    """
    Validates the provided configuration dictionary.

    This function checks if the configuration dictionary contains any reserved
    keys and ensures that the required 'theme' and 'name' settings are present.

    Parameters:
    config (dict[str, Any]): The configuration dictionary to validate.

    Raises:
    ValueError: If a reserved key is found in the config, or if the 'theme'
                setting or 'name' setting within 'theme' is missing.
    """

    for reserved in RESERVED_KEYS:
        if reserved in config:
            raise ValueError("Reserved key in config: {reserved}")

    if "theme" not in config:
        raise ValueError("Missing theme setting config")

    if "name" not in config["theme"]:
        raise ValueError("Missing name setting in confg['theme']")


def load_config(directory: Path) -> dict[str, Any]:
    """
    Loads the configuration from the given directory.

    The configuration is loaded from the first found application.yaml or
    application.yml file in the given directory.

    Raises:
    FileNotFoundError: If no application.yaml/application.yml file is found in
                      the given directory.

    Returns:
    dict[str, Any]: The loaded configuration.
    """
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
    """
    Render a specific template.

    This command renders the specified template and prints the output to stdout.

    Parameters:
    directory (Path): The directory containing the application configuration.
    name (Path): The name of the template to render, relative to the theme.
    """
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
    """
    Build the application project by rendering documents with specified templates.

    This function processes the documents defined in the application's configuration,
    renders them using Jinja2 templates, and outputs the rendered HTML or PDF files.
    It supports options for output directory, PDF generation, and saving intermediary
    HTML files for debugging purposes.

    Args:
        directory (Path): The directory containing the application configuration.
        output_directory (Path | None): The directory to save output files, defaults to the build directory.
        build_pdf (bool): Whether to build PDFs of the documents.
        debug_pdf (bool): Whether to save the intermediary HTML used for PDF generation.

    Raises:
        ValueError: If a reserved key is found in the config, or if the 'theme'
                    setting or 'name' setting within 'theme' is missing.
        FileNotFoundError: If no application.yaml/application.yml file is found in
                          the given directory.
    """

    if output_directory:
        output_directory = output_directory.resolve()
    else:
        output_directory = Path.cwd().resolve()
    with change_working_directory(directory):
        config = load_config(Path.cwd())

        for document in config["documents"]:
            template_file: str | None = config["documents"][document].get("template")
            if template_file is None:
                if "letter" in document:
                    template_file = "letter.html"
                else:
                    template_file = "cv.html"

            LOGGER.info(
                "Rendering document %s with template %s", document, template_file
            )
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
                        document=config["documents"][document],
                        **config,
                    ),
                )

                if build_pdf:
                    pdf_path = tmppath / "output.pdf"
                    pdf_out_path = (output_directory / document).with_suffix(".pdf")
                    pdf.render_file(html_path, pdf_path)
                    shutil.copy2(pdf_path, pdf_out_path)

                    if debug_pdf:
                        shutil.copy2(
                            html_path,
                            (output_directory / document).with_suffix(".pdf.html"),
                        )
                else:
                    shutil.copy2(
                        html_path, (output_directory / document).with_suffix(".html")
                    )


class BuildEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(
        self, directory: Path, build_pdf: bool = False, debug_pdf: bool = False
    ) -> None:
        """
        Initialize the event handler with a directory to monitor and options.

        Parameters:
        directory (Path): The directory to monitor for changes.
        build_pdf (bool): Whether to build PDFs when rebuilding the project.
        debug_pdf (bool): Whether to save the intermediary HTML used for PDF generation.
        """
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
    """
    Build the application project and watch for changes in specified directories.

    This function sets up a directory watcher that rebuilds the project whenever
    changes are detected in the application configuration or theme files.

    Args:
        directory (Path): The directory to build and monitor for changes.
        build_pdf (bool): Whether to build PDFs of the documents.
        debug_pdf (bool): Whether to save the intermediary HTML used for PDF generation.

    Raises:
        KeyboardInterrupt: If the process is interrupted manually.
    """

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
    """
    Main entry point for the easyapply CLI application.

    This function initializes logging and starts the typer application,
    which defines the command-line interface for easyapply.
    """

    init_logging()
    app()


if __name__ == "__main__":
    main()
