import json
import re
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from hinting_diff import (
    GLYPH_CODEPOINT_START,
    add_glyph_codepoints,
    get_named_instances,
    get_sample_text,
    write_hinting_page,
)
from tests.conftest import GLYPH_ORDER


def page_data(page_path: Path) -> dict:
    data_json = re.search(r"var DATA = (.*);\n", page_path.read_text())
    assert data_json is not None
    return json.loads(data_json[1])


@pytest.mark.parametrize("variable", [False, True])
def test_add_glyph_codepoints(font_factory, tmp_path, variable):
    font_path = font_factory(variable=variable)
    output_path = tmp_path.joinpath("output.ttf")
    codepoints = add_glyph_codepoints(font_path, output_path)

    font = TTFont(font_path)
    output_font = TTFont(output_path)
    assert codepoints == {
        name: GLYPH_CODEPOINT_START + glyph_id
        for glyph_id, name in enumerate(font.getGlyphOrder())
        # Except .notdef
        if glyph_id != 0
    }
    # Every glyph can be reached, and the font's own codepoints still work
    output_cmap = output_font.getBestCmap()
    for name, codepoint in codepoints.items():
        assert output_cmap[codepoint] == name
    for codepoint, name in font.getBestCmap().items():
        assert output_cmap[codepoint] == name
    # Only the cmap (and the head's checksum and date) change, so the hinting is
    # kept
    assert sorted(
        tag
        for tag in font.reader.keys()  # noqa: SIM118 (has no `__iter__`)
        if font.reader[tag] != output_font.reader[tag]
    ) == ["cmap", "head"]
    assert {"fpgm", "prep", "cvt "} <= set(output_font.keys())

    # A (3, 10) subtable that's already there is extended
    again_path = tmp_path.joinpath("again.ttf")
    add_glyph_codepoints(output_path, again_path)
    again_cmap = TTFont(again_path)["cmap"]
    assert [(t.platformID, t.platEncID) for t in again_cmap.tables].count((3, 10)) == 1
    assert again_cmap.getBestCmap() == output_cmap


def test_get_sample_text(font_path):
    font = TTFont(font_path)
    # Format, control and space characters are left out too
    for table in font["cmap"].tables:
        if table.isUnicode():
            for codepoint in (0x00AD, 0x0009, 0x00A0):
                table.cmap[codepoint] = "A"
    # In codepoint order, without the space and the combining acute
    assert get_sample_text(font) == "ABa"


def test_get_named_instances(font_factory):
    assert get_named_instances(TTFont(font_factory())) == []
    assert get_named_instances(TTFont(font_factory(variable=True))) == [
        ("Thin", {"wght": 100.0}),
        ("Black", {"wght": 900.0}),
    ]


def test_write_hinting_page(font_factory, tmp_path):
    # The new font has a glyph removed, and one added
    before_path = font_factory("before/Test-Regular.ttf", variable=True)
    after_path = font_factory(
        "after/Test-Regular.ttf",
        glyph_order=[n for n in GLYPH_ORDER if n != "B"] + ["b.alt"],
        variable=True,
    )
    output_path = tmp_path.joinpath("output", "nested")

    page_path = write_hinting_page(before_path, after_path, output_path)

    assert page_path == output_path.joinpath("Test-Regular-hinting.html")
    for name in ("hinting-old-Test-Regular.ttf", "hinting-new-Test-Regular.ttf"):
        assert output_path.joinpath(name).is_file()
    page = page_path.read_text()
    assert "<title>Hinting: Test-Regular.ttf</title>" in page
    assert 'src: url("hinting-old-Test-Regular.ttf")' in page
    data = page_data(page_path)
    glyphs = {glyph["name"]: glyph for glyph in data["glyphs"]}
    assert glyphs["A"] == {
        "name": "A",
        "old": GLYPH_CODEPOINT_START + GLYPH_ORDER.index("A"),
        "new": GLYPH_CODEPOINT_START + GLYPH_ORDER.index("A"),
    }
    assert glyphs["b.alt"]["old"] is None
    # Glyphs that were removed come last
    assert data["glyphs"][-1] == {
        "name": "B",
        "old": GLYPH_CODEPOINT_START + GLYPH_ORDER.index("B"),
        "new": None,
    }
    assert ".notdef" not in glyphs
    assert data["instances"] == [
        {"name": "Thin", "coords": {"wght": 100.0}},
        {"name": "Black", "coords": {"wght": 900.0}},
    ]
    # The new font's characters, rather than its copy's, which encodes every glyph
    assert data["sampleText"] == "Aa"


def test_write_hinting_page_name(font_path, tmp_path):
    page_path = write_hinting_page(font_path, font_path, tmp_path, "page.html")
    assert page_path == tmp_path.joinpath("page.html")
    assert page_data(page_path)["instances"] == []


def test_write_hinting_page_escapes(font_factory, tmp_path):
    # A name that would break the page's HTML or CSS
    font_path = font_factory('A<b>&" #1.ttf')
    page = write_hinting_page(font_path, font_path, tmp_path).read_text()
    assert "<title>Hinting: A&lt;b&gt;&amp;&quot; #1.ttf</title>" in page
    assert 'src: url("hinting-new-A%3Cb%3E%26%22%20%231.ttf")' in page
    assert 'var TITLE = "A<b>&\\" #1";' in page


# Syntax and methods that old browsers don't support, e.g. Internet Explorer 11,
# Chrome 49 and Firefox 52, which hinting is still checked in on old versions of
# Windows. Not a full check, but it catches the usual ones.
UNSUPPORTED_SCRIPT = {
    "const": r"\bconst\s",
    "let": r"\blet\s",
    "arrow function": r"=>",
    "template string": r"`",
    "spread or rest": r"\.\.\.",
    "class": r"\bclass\s+\w+\s*\{",
    "async or await": r"\b(async|await)\b",
    "optional chaining": r"\?\.",
    "nullish coalescing": r"\?\?",
    "for of": r"\bfor\s*\([^)]*\bof\b",
    "replaceChildren()": r"\.replaceChildren\(",
    "append() or prepend()": r"\.(append|prepend)\(",
    "includes()": r"\.includes\(",
    "find() or findIndex()": r"\.find(Index|Last)?\(",
    "Array.from()": r"\bArray\.from\(",
    "Object.entries() or values()": r"\bObject\.(entries|values|assign)\(",
    "String.fromCodePoint()": r"\bfromCodePoint\(",
    "URLSearchParams": r"\bURLSearchParams\b",
    "classList": r"\bclassList\b",
    "fetch()": r"\bfetch\(",
    "Promise": r"\bPromise\b",
}


def test_page_script_works_in_old_browsers(font_path, tmp_path):
    page = write_hinting_page(font_path, font_path, tmp_path).read_text()
    script = re.search(r"<script>(.*)</script>", page, re.DOTALL)
    assert script is not None
    # Without comments, the page's data and strings, which can contain anything
    code = re.sub(r"^var (DATA|TITLE) = .*$", "", script[1], flags=re.MULTILINE)
    code = re.sub(r"//[^\n]*", "", code)
    code = re.sub(r'"(\\.|[^"\\])*"' + r"|'(\\.|[^'\\])*'", '""', code)
    found = [
        name for name, pattern in UNSUPPORTED_SCRIPT.items() if re.search(pattern, code)
    ]
    assert found == []
