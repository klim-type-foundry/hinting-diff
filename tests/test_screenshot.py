import contextlib
import json
import sys
import urllib.parse

import pytest
from PIL import Image

from hinting_diff import (
    open_browser,
    take_screenshots,
    write_hinting_page,
    write_screenshot_list,
)
from hinting_diff.cli import main
from hinting_diff.screenshot import _page_url
from tests.conftest import GLYPH_ORDER


@pytest.fixture(scope="module")
def browser():
    with open_browser() as browser:
        yield browser


def test_take_screenshots(font_path, tmp_path, browser):
    page_path = write_hinting_page(font_path, font_path, tmp_path)
    output_path = tmp_path.joinpath("screenshots")

    screenshots = take_screenshots(page_path, output_path, browser)

    assert [(s.style, s.part) for s in screenshots] == [
        (None, "text"),
        (None, "glyphs-16ppem"),
    ]
    text = screenshots[0]
    assert text.page == page_path
    assert text.old == output_path.joinpath("Test-Regular-text-old.png")
    assert text.new == output_path.joinpath("Test-Regular-text-new.png")
    # The same font, so nothing changed
    assert not any(screenshot.changed for screenshot in screenshots)
    # A line for each size of the waterfall, 9 to 24 ppem
    with Image.open(text.new) as image:
        assert image.height > sum(range(9, 25))


def test_take_screenshots_changed(font_factory, tmp_path, browser):
    # A glyph is removed, so the glyphs change, but the sample text doesn't, as it's
    # the new font's characters
    before_path = font_factory("before/Test-Regular.ttf")
    after_path = font_factory(
        "after/Test-Regular.ttf", glyph_order=[n for n in GLYPH_ORDER if n != "B"]
    )
    page_path = write_hinting_page(before_path, after_path, tmp_path)

    screenshots = take_screenshots(
        page_path, tmp_path, browser, sizes=(10, 12), ppems=[12, 20], text="all"
    )

    assert {s.part: s.changed for s in screenshots} == {
        "text": False,
        "glyphs-12ppem": True,
        "glyphs-20ppem": True,
    }
    with Image.open(screenshots[0].new) as image:
        small_height = image.height
    assert small_height < sum(range(9, 25))


def test_take_screenshots_variable(font_factory, tmp_path, browser):
    font_path = font_factory("Test-VF.ttf", variable=True)
    page_path = write_hinting_page(font_path, font_path, tmp_path)

    screenshots = take_screenshots(page_path, tmp_path, browser)

    # Each named instance, in files named after it
    assert [(s.style, s.part) for s in screenshots] == [
        ("Thin", "text"),
        ("Thin", "glyphs-16ppem"),
        ("Black", "text"),
        ("Black", "glyphs-16ppem"),
    ]
    assert screenshots[2].new == tmp_path.joinpath("Test-VF-Black-text-new.png")
    assert all(screenshot.new.is_file() for screenshot in screenshots)


def test_page_url(tmp_path):
    url = _page_url(tmp_path / "page.html", {"custom": "a+b c&d#e", "capture": "1"})
    page, fragment = url.split("#", 1)
    assert page == tmp_path.joinpath("page.html").resolve().as_uri()
    # Spaces aren't given as "+", which the page reads as a space
    assert fragment == "custom=a%2Bb%20c%26d%23e&capture=1"
    assert urllib.parse.unquote(fragment.split("&")[0]) == "custom=a+b c&d#e"


def test_write_screenshot_list(font_path, tmp_path, browser):
    page_path = write_hinting_page(font_path, font_path, tmp_path)
    output_path = tmp_path.joinpath("screenshots")
    screenshots = take_screenshots(page_path, output_path, browser)

    list_path = write_screenshot_list(screenshots, output_path)

    assert list_path == output_path.joinpath("screenshots.json")
    assert json.loads(list_path.read_text())[0] == {
        "page": "Test-Regular-hinting.html",
        "style": None,
        "part": "text",
        "old": "Test-Regular-text-old.png",
        "new": "Test-Regular-text-new.png",
        "changed": False,
    }


def test_open_browser_without_extra(monkeypatch):
    # As if Playwright wasn't installed
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    with (
        pytest.raises(ImportError, match=r"hinting-diff\[screenshot\]"),
        open_browser(),
    ):
        pass


def test_main_screenshot(font_path, tmp_path, capsys, monkeypatch, browser):
    # The module's browser, as only one Playwright can run at a time
    monkeypatch.setattr(
        "hinting_diff.cli.open_browser", lambda: contextlib.nullcontext(browser)
    )
    monkeypatch.setattr(sys, "platform", "linux")
    output_path = tmp_path.joinpath("out")
    args = [str(font_path), str(font_path), "-o", str(output_path)]

    assert main([*args, "--screenshot", "--screenshot-ppem", "12", "20"]) == 0

    list_path = output_path.joinpath("screenshots", "screenshots.json")
    parts = [screenshot["part"] for screenshot in json.loads(list_path.read_text())]
    assert parts == ["text", "glyphs-12ppem", "glyphs-20ppem"]
    out, err = capsys.readouterr()
    # The page, then the screenshots that changed (none), then the list
    assert out.splitlines() == [
        str(output_path.joinpath("Test-Regular-hinting.html")),
        str(list_path),
    ]
    assert "only apply TrueType hinting on Windows" in err
    assert "0 of 3 screenshots changed" in err


def test_main_screenshot_error(font_path, tmp_path, capsys, monkeypatch):
    def no_browser():
        raise RuntimeError("a browser couldn't be started")

    monkeypatch.setattr("hinting_diff.cli.open_browser", no_browser)
    args = [str(font_path), str(font_path), "-o", str(tmp_path), "--screenshot"]
    # The page is still written
    assert main(args) == 1
    assert tmp_path.joinpath("Test-Regular-hinting.html").is_file()
    assert "error: a browser couldn't be started" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--screenshot-sizes", "24-9"),
        ("--screenshot-sizes", "0-9"),
        ("--screenshot-sizes", "9"),
        ("--screenshot-ppem", "7"),
        ("--screenshot-ppem", "70"),
    ],
)
def test_main_screenshot_bad_sizes(font_path, capsys, option, value):
    with pytest.raises(SystemExit) as exit_info:
        main([str(font_path), str(font_path), "--screenshot", option, value])
    assert exit_info.value.code == 2
    assert repr(value) in capsys.readouterr().err
