from importlib.metadata import PackageNotFoundError, version

from hinting_diff.git import save_fonts_at_commit
from hinting_diff.matching import FontMatch, find_fonts, match_fonts
from hinting_diff.page import (
    GLYPH_CODEPOINT_START,
    add_glyph_codepoints,
    get_named_instances,
    get_sample_text,
    write_hinting_page,
    write_index_page,
)
from hinting_diff.screenshot import (
    Screenshot,
    open_browser,
    take_screenshots,
    write_screenshot_list,
)

try:
    # The version is set by the VERSION file, see pyproject.toml
    __version__ = version("hinting-diff")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

__all__ = [
    "GLYPH_CODEPOINT_START",
    "FontMatch",
    "Screenshot",
    "__version__",
    "add_glyph_codepoints",
    "find_fonts",
    "get_named_instances",
    "get_sample_text",
    "match_fonts",
    "open_browser",
    "save_fonts_at_commit",
    "take_screenshots",
    "write_hinting_page",
    "write_index_page",
    "write_screenshot_list",
]
