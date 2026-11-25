"""
Takes screenshots of hinting pages in a browser, to review fonts' hinting without
opening the pages, e.g. in CI. Browsers only apply TrueType hinting on Windows, so
the screenshots only show it there.

Needs the `screenshot` extra, e.g. `pip install "hinting-diff[screenshot]"`, and a
browser: Microsoft Edge on Windows, or Playwright's Chromium elsewhere (installed
with `playwright install chromium`).
"""

import json
import re
import sys
import urllib.parse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Browser, ViewportSize

DEFAULT_SIZES = (9, 24)
DEFAULT_PPEMS = (16,)
DEFAULT_TEXT = "basic"
# Wide enough for Basic Latin at 24 ppem on one line, as the text waterfall's lines
# are cut off at the right
_VIEWPORT: "ViewportSize" = {"width": 1600, "height": 900}
# Milliseconds to wait for a page's fonts to load
_READY_TIMEOUT = 30_000
_EXTRA_MESSAGE = (
    'screenshots need the "screenshot" extra, e.g. '
    'pip install "hinting-diff[screenshot]"'
)


@dataclass(frozen=True)
class Screenshot:
    """
    Screenshots of a part of a hinting page in the old and the new font: the sample
    text as a waterfall ("text"), or the glyphs at a size (e.g. "glyphs-16ppem").
    `style` is a variable font's instance, or None for a static font. `changed` is
    whether the two screenshots differ.
    """

    page: Path
    style: str | None
    part: str
    old: Path
    new: Path
    changed: bool


@contextmanager
def open_browser() -> Iterator["Browser"]:
    """
    Starts a headless browser for take_screenshots(), and closes it afterwards:
    Microsoft Edge on Windows, where it's always installed, or Playwright's
    Chromium. Raises ImportError without the "screenshot" extra, and RuntimeError
    if no browser can be started.
    """
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError as error:
        raise ImportError(_EXTRA_MESSAGE) from error

    with sync_playwright() as playwright:
        browser = None
        if sys.platform == "win32":
            try:
                browser = playwright.chromium.launch(channel="msedge")
            except Error:
                pass
        if browser is None:
            try:
                browser = playwright.chromium.launch()
            except Error as error:
                raise RuntimeError(
                    "a browser couldn't be started, so install Playwright's "
                    "Chromium with: playwright install chromium"
                ) from error
        try:
            yield browser
        finally:
            browser.close()


def _file_name(text: str) -> str:
    # e.g. "Bold Italic" as "Bold-Italic"
    return re.sub(r"[^\w.]+", "-", text).strip("-")


def _page_url(page_path: Path, settings: dict[str, str]) -> str:
    # Spaces as %20 rather than "+", which the page reads as a space too, so a "+"
    # in the text stays one
    fragment = urllib.parse.urlencode(settings, quote_via=urllib.parse.quote)
    return f"{page_path.resolve().as_uri()}#{fragment}"


def _images_differ(old_path: Path, new_path: Path) -> bool:
    from PIL import Image, ImageChops

    with Image.open(old_path) as old, Image.open(new_path) as new:
        if old.size != new.size:
            return True
        difference = ImageChops.difference(old.convert("RGB"), new.convert("RGB"))
        return difference.getbbox() is not None


def take_screenshots(
    page_path: Path,
    output_path: Path,
    browser: "Browser",
    sizes: tuple[int, int] = DEFAULT_SIZES,
    ppems: Sequence[int] = DEFAULT_PPEMS,
    text: str = DEFAULT_TEXT,
) -> list[Screenshot]:
    """
    Takes screenshots of a hinting page (see write_hinting_page()) in the old and
    the new font, in a browser from open_browser(): the sample text as a waterfall
    of `sizes` (smallest and largest, in ppem), and the glyphs at each of `ppems`.
    For a variable font, they're taken at each named instance. `text` is the sample
    text: "all" (every character the new font encodes), "basic" (Basic Latin) or
    your own text. Saves PNGs named after the page in `output_path`, and returns the
    screenshots.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    name = _file_name(page_path.stem.removesuffix("-hinting"))
    page = browser.new_page(viewport=_VIEWPORT, device_scale_factor=1)
    try:
        # Every setting is given, so none are kept from an earlier page
        settings = {
            "ppem": str(ppems[0]),
            "waterfall": "1",
            "sizes": f"{sizes[0]}-{sizes[1]}",
            "glyph": "",
            "filter": "",
            "capture": "1",
        }
        if text in ("all", "basic"):
            settings["text"] = text
        else:
            settings["custom"] = text

        def load(**more_settings: str) -> None:
            # A new page each time, as a change to only the URL's fragment doesn't
            # load it again
            page.goto("about:blank")
            page.goto(_page_url(page_path, {**settings, **more_settings}))
            page.wait_for_selector(
                "html[data-ready=true]", state="attached", timeout=_READY_TIMEOUT
            )

        load(font="new")
        styles: list[str | None] = list(
            page.evaluate("DATA.instances.map(function (i) { return i.name; })")
        ) or [None]

        screenshots = []
        for style in styles:
            prefix = name if style is None else f"{name}-{_file_name(style)}"
            style_settings = {} if style is None else {"style": style}
            paths: dict[str, dict[str, Path]] = {}
            for font in ("old", "new"):
                for index, ppem in enumerate(ppems):
                    load(font=font, ppem=str(ppem), **style_settings)
                    # Without the titles, which name the font
                    if index == 0:
                        text_path = output_path / f"{prefix}-text-{font}.png"
                        page.locator("#text-waterfall").screenshot(path=text_path)
                        paths.setdefault("text", {})[font] = text_path
                    part = f"glyphs-{ppem}ppem"
                    glyphs_path = output_path / f"{prefix}-{part}-{font}.png"
                    page.locator("#glyphs").screenshot(path=glyphs_path)
                    paths.setdefault(part, {})[font] = glyphs_path
            for part, part_paths in paths.items():
                screenshots.append(
                    Screenshot(
                        page=page_path,
                        style=style,
                        part=part,
                        old=part_paths["old"],
                        new=part_paths["new"],
                        changed=_images_differ(part_paths["old"], part_paths["new"]),
                    )
                )
        return screenshots
    finally:
        page.close()


def write_screenshot_list(
    screenshots: list[Screenshot],
    output_path: Path,
    file_name: str = "screenshots.json",
) -> Path:
    """
    Writes a list of screenshots as JSON in `output_path`, with paths relative to
    it, e.g. for a CI workflow to show the ones that changed. Returns its path.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    list_path = output_path / file_name

    def relative(path: Path) -> str:
        return path.resolve().relative_to(output_path.resolve()).as_posix()

    list_path.write_text(
        json.dumps(
            [
                {
                    "page": screenshot.page.name,
                    "style": screenshot.style,
                    "part": screenshot.part,
                    "old": relative(screenshot.old),
                    "new": relative(screenshot.new),
                    "changed": screenshot.changed,
                }
                for screenshot in screenshots
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return list_path
