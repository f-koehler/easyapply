import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

LOGGER = logging.getLogger(__name__)


def render_file(path: Path, output: Path, delay: int = 100) -> None:
    with sync_playwright() as p:
        LOGGER.info("Launching chromium headless")
        browser = p.chromium.launch(headless=True)

        LOGGER.info("Opening HTML file")
        page = browser.new_page()
        page.goto(f"file://{path.resolve()}")

        LOGGER.info("Waiting for page load to finish")
        page.wait_for_load_state("networkidle")

        LOGGER.info("Rendering PDF")
        page.pdf(
            path=output,
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
        )

        LOGGER.info("Closing browser")
        browser.close()
