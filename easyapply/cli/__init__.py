from pathlib import Path

import typer
import yaml

from .. import pdf, themes

app = typer.Typer()


@app.command()
def list_themes():
    print("List of themes")


@app.command()
def build():
    with open("application.yaml") as fptr:
        config = yaml.safe_load(fptr)
    template = themes.load_template(config["theme"])
    (Path.cwd() / "cv.html").write_text(
        template.render(
            theme=config["theme"],
            cv=config["cv"],
            theme_dir=Path(template.filename).parent.parent,
        ),
    )

    pdf.render_file(Path.cwd() / "cv.html", Path.cwd() / "cv.pdf")


def main():
    app()


if __name__ == "__main__":
    main()
