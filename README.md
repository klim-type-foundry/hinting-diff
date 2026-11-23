# hinting-diff

Compare the TrueType hinting of two versions of a font in a browser.

`hinting-diff` writes an HTML page that shows every glyph of a font, encoded or
not, rendered with its hinting at a size in pixels per em (ppem), for the old
and the new version of the font. Click **old**/**new** to switch between them
and see what changed.

Browsers only apply TrueType hinting on Windows, so open the page on Windows.

## Install

```shell
pip install "hinting-diff @ git+https://github.com/klim-type-foundry/hinting-diff@v0.1.0"
```

It needs Python 3.10 or later, and [fontTools](https://github.com/fonttools/fonttools).

## Usage

```shell
hinting-diff old/Family-Regular.ttf new/Family-Regular.ttf -o hinting-diff/
```

This writes `hinting-diff/Family-Regular-hinting.html`, with copies of both
fonts next to it, and prints the page's path. Open it in a browser on Windows.

The page has:

- **Sample text**, which starts as every character the new font encodes
  (without combining marks or spaces), for a quick look over the whole character
  set. You can edit it.
- **Every glyph**, at the **Font Size** you choose (48 ppem to start with).
  Hover over a glyph to see its name, or filter the glyphs by name. Glyphs that
  are only in one of the fonts say so.
- **A waterfall** of a glyph from 8 to 64 ppem: click a glyph to show it.
- For variable fonts, an **Instance** menu with the font's named instances.

The size, font, filter, selected glyph and edited text are kept for the browser
tab's session, so they stay the same when you open another font's page in the
same tab.

Sizes are in device pixels, so they stay the same with browser zoom or display
scaling (e.g. 150% in Windows), which change how many device pixels a CSS pixel
is.

### Showing the page in a report

A page that shows the hinting page in a frame can pick a variable font's
instance by adding its name to the URL, e.g.
`Family-Regular-hinting.html#style=Bold`. This hides the page's own
**Instance** menu.

### From Python

```python
from pathlib import Path

from hinting_diff import write_hinting_page

page_path = write_hinting_page(
    Path("old/Family-Regular.ttf"),
    Path("new/Family-Regular.ttf"),
    Path("hinting-diff"),
    page_name="Family-Regular.html",  # Optional
)
```

## How it works

Browsers can only show characters, not glyphs, so the fonts on the page are
copies with each glyph mapped to a Private Use Area codepoint, from U+F0000.
Only their `cmap` table changes: the other tables, including `glyf`, `fpgm`,
`prep` and `cvt `, are saved as they are, so the hinting is kept. Glyphs that a
variable font swaps with feature variations (`rvrn`) at the selected instance
show the swapped glyph, as they would in use.

## Development

With [uv](https://docs.astral.sh/uv/) installed:

```shell
make init
make test
```

`make init` sets up the Python environment in `.venv/` with the exact package
versions from `uv.lock`, and installs the [pre-commit](https://pre-commit.com/)
hooks, which run Ruff, mypy and some general file checks.

To release a new version, change the version in `VERSION` and merge it into
`main`. The release workflow runs the checks and creates a GitHub release
tagged with the version (e.g. `v0.1.0`).

## Licence

[Apache License 2.0](LICENSE.txt)
