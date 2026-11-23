import array
from collections.abc import Callable
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables import ttProgram

# Encoded glyphs, with a combining mark and a space, and an unencoded one
CMAP = {0x20: "space", 0x41: "A", 0x42: "B", 0x61: "a", 0x0301: "acutecomb"}
GLYPH_ORDER = [".notdef", *CMAP.values(), "a.alt"]


def _rectangle_glyph(width: int):
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((width - 50, 700))
    pen.lineTo((width - 50, 0))
    pen.closePath()
    return pen.glyph()


def build_font(
    path: Path,
    glyph_order: list[str] = GLYPH_ORDER,
    variable: bool = False,
) -> Path:
    """
    Saves a small TrueType font with some hinting tables (fpgm, prep and cvt), so
    the tests don't need font files, and returns its path.
    """
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap({c: n for c, n in CMAP.items() if n in glyph_order})
    builder.setupGlyf(
        {
            name: (
                TTGlyphPen(None).glyph() if name == "space" else _rectangle_glyph(500)
            )
            for name in glyph_order
        }
    )
    builder.setupHorizontalMetrics({name: (500, 50) for name in glyph_order})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    if variable:
        builder.setupFvar(
            axes=[("wght", 100, 400, 900, "Weight")],
            instances=[
                {"location": {"wght": 100}, "stylename": "Thin"},
                {"location": {"wght": 900}, "stylename": "Black"},
            ],
        )
    font = builder.font
    for tag in ("fpgm", "prep"):
        table = newTable(tag)
        table.program = ttProgram.Program()
        table.program.fromAssembly(["PUSHB[ ]", "0", "POP[ ]"])
        font[tag] = table
    font["cvt "] = newTable("cvt ")
    font["cvt "].values = array.array("h", [0, 700])
    font.save(path)
    return path


@pytest.fixture
def font_factory(tmp_path: Path) -> Callable[..., Path]:
    def factory(name: str = "Test-Regular.ttf", **kwargs) -> Path:
        path = tmp_path.joinpath("fonts", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        return build_font(path, **kwargs)

    return factory


@pytest.fixture
def font_path(font_factory) -> Path:
    return font_factory()
