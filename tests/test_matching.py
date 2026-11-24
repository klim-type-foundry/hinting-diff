import pytest

from hinting_diff import FontMatch, find_fonts, match_fonts


def test_find_fonts(font_factory, tmp_path):
    fonts_path = tmp_path.joinpath("fonts")
    regular_path = font_factory("static/Test-Regular.ttf")
    # In subfolders too, and whatever the suffix's case
    bold_path = font_factory("static/bold/Test-Bold.TTF")
    fonts_path.joinpath("static", "Test-Regular.otf").write_bytes(b"")
    fonts_path.joinpath("static", "notes.txt").write_text("")
    # Fonts given on their own are used whatever their suffix
    other_path = font_factory("Test-Other.font")

    assert find_fonts([fonts_path.joinpath("static"), other_path]) == [
        bold_path,
        other_path,
        regular_path,
    ]


def test_find_fonts_errors(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing.ttf not found"):
        find_fonts([tmp_path.joinpath("missing.ttf")])
    with pytest.raises(ValueError, match="no TrueType fonts"):
        find_fonts([tmp_path])


def test_match_fonts(font_factory, tmp_path):
    fonts_path = tmp_path.joinpath("fonts")
    old_regular = font_factory("old/Test-Regular.ttf")
    old_bold = font_factory("old/Test-Bold.ttf")
    removed = font_factory("old/Test-Removed.ttf")
    new_regular = font_factory("new/Test-Regular.ttf")
    new_bold = font_factory("new/Test-Bold.ttf")
    added = font_factory("new/Test-Added.ttf")

    expected = FontMatch(
        pairs=[(old_bold, new_bold), (old_regular, new_regular)],
        only_before=[removed],
        only_after=[added],
    )
    # Folders, or fonts, e.g. from a shell's `old/*.ttf`
    assert match_fonts([fonts_path / "old"], [fonts_path / "new"]) == expected
    assert (
        match_fonts([old_regular, old_bold, removed], [added, new_bold, new_regular])
        == expected
    )


def test_match_fonts_single_fonts(font_factory):
    # Fonts given on their own are compared whatever their names
    before_path = font_factory("Test-Regular-old.ttf")
    after_path = font_factory("Test-Regular.ttf")
    assert match_fonts([before_path], [after_path]) == FontMatch(
        [(before_path, after_path)], [], []
    )


def test_match_fonts_single_font_in_folders(font_factory, tmp_path):
    # But fonts in folders are matched by name, even if there's one of each
    before_path = font_factory("old/Test-Regular-old.ttf")
    after_path = font_factory("new/Test-Regular.ttf")
    fonts_path = tmp_path.joinpath("fonts")
    assert match_fonts([fonts_path / "old"], [fonts_path / "new"]) == FontMatch(
        [], [before_path], [after_path]
    )


def test_match_fonts_same_names(font_factory, tmp_path):
    font_factory("old/a/Test-Regular.ttf")
    font_factory("old/b/Test-Regular.ttf")
    font_factory("new/Test-Regular.ttf")
    fonts_path = tmp_path.joinpath("fonts")
    with pytest.raises(ValueError, match="more than one old font"):
        match_fonts([fonts_path / "old"], [fonts_path / "new"])
