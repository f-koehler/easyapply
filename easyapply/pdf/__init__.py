import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright


def render_file(path: Path, output: Path, delay: int = 100) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(f"file://{path.resolve()}")
        page.pdf(
            path=output,
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
        )
        page.wait_for_load_state("networkidle")
        browser.close()
