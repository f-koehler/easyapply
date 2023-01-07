import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
import time


def render_file(path: Path, output: Path, delay: int = 100) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{path.resolve()}")
        page.wait_for_load_state("networkidle")
        page.pdf(
            path=output,
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
        )
        browser.close()
