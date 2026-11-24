"""
Writes a page to compare the TrueType hinting of two versions of a font in a
browser.
"""

import html
import json
import os
import unicodedata
import urllib.parse
from importlib import resources
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

# Each glyph is mapped to a codepoint from here, in Supplementary Private Use
# Area-A, so unencoded glyphs can be shown in a browser too
GLYPH_CODEPOINT_START = 0xF0000
_GLYPH_CODEPOINT_END = 0xFFFFD

# Characters left out of the sample text: combining marks, which would stack on
# the character before them, and characters that show nothing
_SAMPLE_SKIPPED_CATEGORIES = frozenset({"Mn", "Me", "Cc", "Cf", "Cs", "Zs", "Zl", "Zp"})


def add_glyph_codepoints(font_path: Path, output_path: Path) -> dict[str, int]:
    """
    Saves a copy of a font with a Private Use Area codepoint for each glyph, so
    unencoded glyphs can be shown in a browser too. Only the cmap table changes, so
    the hinting is kept. Returns the codepoint of each glyph.
    """
    # Tables that aren't loaded are saved as they are, e.g. glyf, fpgm, prep and cvt.
    # The glyph order is read from another copy, as reading it loads the post table,
    # which would then be recompiled.
    glyph_order_font = TTFont(font_path, lazy=True)
    glyph_order = glyph_order_font.getGlyphOrder()
    glyph_order_font.close()
    font = TTFont(font_path, lazy=True)
    font.setGlyphOrder(glyph_order)
    if len(glyph_order) > _GLYPH_CODEPOINT_END - GLYPH_CODEPOINT_START:
        raise ValueError(f"{font_path.name} has too many glyphs")
    # Except .notdef: a character mapped to it isn't saved, and browsers show it in
    # another font
    codepoints = {
        glyph_name: GLYPH_CODEPOINT_START + glyph_id
        for glyph_id, glyph_name in enumerate(glyph_order)
        if glyph_id != 0
    }
    cmap_table = font["cmap"]
    # A (3, 10) subtable is needed for codepoints above U+FFFF. Windows prefers it
    # to the (3, 1) subtable, so it needs the font's own mappings too.
    subtable = cmap_table.getcmap(3, 10)
    if subtable is None:
        subtable = CmapSubtable.newSubtable(12)
        subtable.platformID = 3
        subtable.platEncID = 10
        subtable.language = 0
        subtable.cmap = dict(font.getBestCmap())
        cmap_table.tables.append(subtable)
    subtable.cmap.update({codepoint: name for name, codepoint in codepoints.items()})
    font.save(output_path)
    font.close()
    return codepoints


def get_sample_text(font: TTFont) -> str:
    """
    Returns every character a font encodes, in codepoint order, for an overview of
    its glyph set, without combining marks or characters that show nothing.
    """
    return "".join(
        char
        for char in map(chr, sorted(font.getBestCmap()))
        if unicodedata.category(char) not in _SAMPLE_SKIPPED_CATEGORIES
    )


def get_named_instances(font: TTFont) -> list[tuple[str, dict[str, float]]]:
    """
    Returns a variable font's named instances as (name, coordinates). Instances
    without a Windows English name are left out.
    """
    if "fvar" not in font:
        return []
    instances: list[tuple[str, dict[str, float]]] = []
    for instance in font["fvar"].instances:
        name = font["name"].getName(instance.subfamilyNameID, 3, 1, 0x409)
        if name is not None:
            instances.append((name.toUnicode(), instance.coordinates))
    return instances


def _css_url(filename: str) -> str:
    """
    Returns a file's name for a CSS url() in a page's <style>, where HTML entities
    aren't decoded, so it's URL-encoded instead (e.g. "#" would start a fragment).
    """
    return urllib.parse.quote(filename)


def _script_json(value: object) -> str:
    # Escape "</" so the data can't close the script element
    return json.dumps(value).replace("</", "<\\/")


def write_hinting_page(
    before_path: Path,
    after_path: Path,
    output_path: Path,
    page_name: str | None = None,
) -> Path:
    """
    Writes a page to inspect the TrueType hinting of two versions of a font on
    Windows: every glyph, encoded or not, in both fonts at a chosen size in pixels
    per em, and a waterfall of a glyph's sizes. The page and copies of the fonts are
    saved in `output_path`, and the page is named `page_name` (by default, the new
    font's name with "-hinting.html"). Returns the page's path.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    page_path = output_path.joinpath(page_name or f"{after_path.stem}-hinting.html")
    before_font_name = f"hinting-old-{after_path.name}"
    after_font_name = f"hinting-new-{after_path.name}"
    before_codepoints = add_glyph_codepoints(
        before_path, output_path.joinpath(before_font_name)
    )
    after_codepoints = add_glyph_codepoints(
        after_path, output_path.joinpath(after_font_name)
    )
    # The new font's glyph order, then glyphs that were removed
    glyphs = [
        {"name": name, "old": before_codepoints.get(name), "new": codepoint}
        for name, codepoint in after_codepoints.items()
    ] + [
        {"name": name, "old": codepoint, "new": None}
        for name, codepoint in before_codepoints.items()
        if name not in after_codepoints
    ]
    after_font = TTFont(after_path, lazy=True)
    instances = [
        {"name": name, "coords": coords}
        for name, coords in get_named_instances(after_font)
    ]
    sample_text = get_sample_text(after_font)
    after_font.close()
    data = {"glyphs": glyphs, "instances": instances, "sampleText": sample_text}
    template = resources.files("hinting_diff").joinpath("page.html").read_text("utf-8")
    page_path.write_text(
        template.replace("{{title}}", html.escape(after_path.name))
        .replace("{{title_json}}", _script_json(after_path.stem))
        .replace("{{before_font}}", _css_url(before_font_name))
        .replace("{{after_font}}", _css_url(after_font_name))
        .replace("{{hinting_json}}", _script_json(data)),
        encoding="utf-8",
    )
    return page_path


_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hinting</title>
<style>
/* The look of the hinting pages (see page.html) */
html {{ font-family: sans-serif; }}
body {{ font-family: Helvetica; }}
.box-title {{ width: 100%; font-size: 8pt; font-weight: 700;
  border-top: 1px solid black; padding-top: 5px; margin-bottom: 10pt;
  display: block; }}
.warning {{ font-size: 9pt; }}
ul {{ padding: 0; list-style: none; }}
li {{ margin-bottom: 4pt; }}
a {{ color: black; }}
</style>
</head>
<body>
<h2><b>Hinting</b></h2>
<p class="warning">Browsers only apply TrueType hinting on Windows, so open these
pages on Windows to inspect it. Open them in the same tab to keep the same settings
on each page.</p>
<div class="box-title">{count}</div>
<ul>
{links}
</ul>
</body>
</html>
"""


def write_index_page(
    page_paths: list[Path], output_path: Path, page_name: str = "index.html"
) -> Path:
    """
    Writes a page that links to hinting pages, e.g. one for each font of a family,
    in `output_path`, named `page_name`. Returns the page's path.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    index_path = output_path.joinpath(page_name)
    links = "\n".join(
        '<li><a href="{href}">{name}</a></li>'.format(
            href=html.escape(
                urllib.parse.quote(
                    Path(os.path.relpath(page_path, output_path)).as_posix()
                )
            ),
            name=html.escape(page_path.stem.removesuffix("-hinting")),
        )
        for page_path in page_paths
    )
    index_path.write_text(
        _INDEX_TEMPLATE.format(
            count=f"{len(page_paths)} font{'' if len(page_paths) == 1 else 's'}",
            links=links,
        ),
        encoding="utf-8",
    )
    return index_path
