import shutil
import subprocess
from pathlib import Path


def find_chromium() -> Path:
    if path := shutil.which("chromium"):
        return Path(path)

    raise RuntimeError("Chromium not found")


def render_file(path: Path, output: Path, delay: int = 100) -> None:
    cmd = [
        str(find_chromium()),
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--virtual-time-budget={delay}",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output}",
        f"file://{path.resolve()}",
    ]
    subprocess.check_output(cmd)
