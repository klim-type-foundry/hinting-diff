"""
Matches the old and new versions of fonts, given as fonts or folders of fonts, by
their file names.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple


class FontMatch(NamedTuple):
    """The fonts to compare, and the fonts that are only in one of the sets."""

    pairs: list[tuple[Path, Path]]
    """Each old font and the new font with the same file name."""
    only_before: list[Path]
    """Old fonts without a new font with the same file name."""
    only_after: list[Path]
    """New fonts without an old font with the same file name."""


def find_fonts(paths: Iterable[Path]) -> list[Path]:
    """
    Returns the fonts in `paths`: fonts as they are, and every TrueType font (.ttf)
    in folders and their subfolders, in file name order. Raises
    `FileNotFoundError` for a path that doesn't exist and `ValueError` for a folder
    without TrueType fonts.
    """
    fonts: list[Path] = []
    for path in paths:
        if path.is_dir():
            # Not `glob("**/*.ttf")`, which is case-sensitive on Linux, and
            # `case_sensitive` needs Python 3.12
            folder_fonts = [
                font_path
                for font_path in path.rglob("*")
                if font_path.suffix.lower() == ".ttf" and font_path.is_file()
            ]
            if not folder_fonts:
                raise ValueError(f"no TrueType fonts (.ttf) in {path}")
            fonts.extend(folder_fonts)
        elif path.is_file():
            fonts.append(path)
        else:
            raise FileNotFoundError(f"{path} not found")
    return sorted(fonts, key=lambda font_path: (font_path.name, str(font_path)))


def _fonts_by_name(fonts: list[Path], label: str) -> dict[str, Path]:
    fonts_by_name: dict[str, Path] = {}
    for font_path in fonts:
        other_path = fonts_by_name.setdefault(font_path.name, font_path)
        if other_path != font_path:
            raise ValueError(
                f"more than one {label} font is named {font_path.name}: "
                f"{other_path} and {font_path}"
            )
    return fonts_by_name


def match_fonts(before_paths: Iterable[Path], after_paths: Iterable[Path]) -> FontMatch:
    """
    Matches the old fonts (`before_paths`) with the new ones (`after_paths`) by
    their file names. Each can be a font or a folder of fonts (see `find_fonts()`).
    A single old font and a single new font are compared whatever their names.
    Raises `ValueError` if two old or two new fonts have the same file name.
    """
    before_paths = list(before_paths)
    after_paths = list(after_paths)
    before_fonts = find_fonts(before_paths)
    after_fonts = find_fonts(after_paths)
    # Fonts given on their own, rather than found in folders, are compared even if
    # they're named differently, e.g. `Family-Regular-old.ttf`
    if (
        len(before_paths) == len(after_paths) == 1
        and before_paths[0].is_file()
        and after_paths[0].is_file()
    ):
        return FontMatch([(before_fonts[0], after_fonts[0])], [], [])
    before_by_name = _fonts_by_name(before_fonts, "old")
    after_by_name = _fonts_by_name(after_fonts, "new")
    return FontMatch(
        pairs=[
            (before_by_name[name], after_path)
            for name, after_path in after_by_name.items()
            if name in before_by_name
        ],
        only_before=[
            before_path
            for name, before_path in before_by_name.items()
            if name not in after_by_name
        ],
        only_after=[
            after_path
            for name, after_path in after_by_name.items()
            if name not in before_by_name
        ],
    )
