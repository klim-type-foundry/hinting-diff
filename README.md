# hinting-diff

Compare the TrueType hinting of two versions of a font in a browser.

`hinting-diff` writes an HTML page that shows every glyph of a font, encoded or
not, rendered with its hinting at a size in pixels per em (ppem), for the old
and the new version of the font. Click **old**/**new** to switch between them
and see what changed.

Browsers only apply TrueType hinting on Windows, so open the page on Windows.

## Install

```shell
pip install hinting-diff
```

It needs Python 3.10 or later, and installs
[fontTools](https://github.com/fonttools/fonttools) too.

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

## Python API

Everything the command does is available from Python too, e.g. to make hinting
pages as part of a bigger report.

### Writing a page

`write_hinting_page()` does the same as the `hinting-diff` command:

```python
from pathlib import Path

from hinting_diff import write_hinting_page

page_path = write_hinting_page(
    Path("old/Family-Regular.ttf"),
    Path("new/Family-Regular.ttf"),
    Path("hinting-diff"),
)
print(page_path)  # hinting-diff/Family-Regular-hinting.html
```

Its arguments are:

- `before_path`: the old font (TTF).
- `after_path`: the new font (TTF).
- `output_path`: the folder for the page and the copies of the fonts. It's made if
  it doesn't exist yet.
- `page_name` (optional): the page's file name. By default, it's the new font's
  name with `-hinting.html`, e.g. `Family-Regular-hinting.html`.

It returns the page's path. The copies of the fonts are saved next to the page as
`hinting-old-<new font's file name>` and `hinting-new-<new font's file name>`, so
pages for several fonts can share a folder:

```python
from pathlib import Path

from hinting_diff import write_hinting_page

for after_path in sorted(Path("new").glob("*.ttf")):
    before_path = Path("old", after_path.name)
    if before_path.is_file():
        write_hinting_page(before_path, after_path, Path("hinting-diff"))
```

Unlike the command, it doesn't check that the fonts exist first: a missing or
broken font raises fontTools' or Python's own error (e.g. `FileNotFoundError`),
and a font with too many glyphs to map to Private Use Area codepoints raises a
`ValueError`.

### Lower-level functions

The functions the page is made with can be used on their own:

- `add_glyph_codepoints(font_path, output_path)` saves a copy of a font with each
  glyph mapped to a Private Use Area codepoint (see
  [How it works](#how-it-works)), and returns a `dict` of each glyph's name and
  codepoint. `.notdef` isn't mapped.
- `get_sample_text(font)` returns every character a `TTFont` encodes, in
  codepoint order, without combining marks or characters that show nothing.
- `get_named_instances(font)` returns a variable `TTFont`'s named instances as a
  list of `(name, coordinates)`, e.g. `("Bold", {"wght": 700.0})`. It returns an
  empty list for a static font.
- `GLYPH_CODEPOINT_START` is the codepoint the first glyph is mapped to
  (`0xF0000`). A glyph's codepoint is this plus its glyph ID.

```python
from pathlib import Path

from fontTools.ttLib import TTFont

from hinting_diff import add_glyph_codepoints, get_named_instances

codepoints = add_glyph_codepoints(
    Path("new/Family-Regular.ttf"), Path("Family-Regular-pua.ttf")
)
print(f"U+{codepoints['a']:X}")  # e.g. U+F0024

with TTFont("new/Family-Regular.ttf", lazy=True) as font:
    for name, coordinates in get_named_instances(font):
        print(name, coordinates)
```

`hinting_diff.__version__` is the package's version.

## How it works

Browsers can only show characters, not glyphs, so the fonts on the page are
copies with each glyph mapped to a Private Use Area codepoint, from U+F0000.
Only their `cmap` table changes: the other tables, including `glyf`, `fpgm`,
`prep` and `cvt `, are saved as they are, so the hinting is kept. Glyphs that a
variable font swaps with feature variations (`rvrn`) at the selected instance
show the swapped glyph, as they would in use.

## Contributing

Bug reports, ideas and pull requests are welcome: see the
[contributing guide](https://github.com/klim-type-foundry/hinting-diff/blob/main/CONTRIBUTING.md)
for how to set up the project and make a change. Please report security
problems privately, as the
[security policy](https://github.com/klim-type-foundry/hinting-diff/blob/main/SECURITY.md)
explains.

## Licence

[Apache License 2.0](https://github.com/klim-type-foundry/hinting-diff/blob/main/LICENSE.txt)
