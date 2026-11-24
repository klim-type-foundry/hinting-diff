import os
import subprocess

import pytest
from fontTools.ttLib import TTFont

from hinting_diff import save_fonts_at_commit
from hinting_diff.cli import main
from tests.conftest import GLYPH_ORDER, build_font


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """
    A git repository with two commits of fonts. The first has Regular, Bold and
    Removed; the second changes Regular. Then, without committing, Regular changes
    again, Removed is deleted and Added is added.
    """
    # Without the user's or the system's git settings, e.g. commit signing
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo_path = tmp_path.joinpath("repo")
    fonts_path = repo_path.joinpath("fonts", "ttf")
    fonts_path.mkdir(parents=True)

    def git(*args):
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    for name in ("Test-Regular.ttf", "Test-Bold.ttf", "Test-Removed.ttf"):
        build_font(fonts_path.joinpath(name))
    fonts_path.joinpath("notes.txt").write_text("")
    git("add", ".")
    git("commit", "-q", "-m", "First")
    git("tag", "first")
    build_font(fonts_path.joinpath("Test-Regular.ttf"), glyph_order=GLYPH_ORDER[:-1])
    git("commit", "-q", "-am", "Second")
    build_font(fonts_path.joinpath("Test-Regular.ttf"), glyph_order=GLYPH_ORDER[:-2])
    fonts_path.joinpath("Test-Removed.ttf").unlink()
    build_font(fonts_path.joinpath("Test-Added.ttf"))
    return repo_path


def glyph_count(font_path):
    with TTFont(font_path) as font:
        return len(font.getGlyphOrder())


def test_save_fonts_at_commit(repo, tmp_path):
    fonts_path = repo.joinpath("fonts", "ttf")
    output_path = tmp_path.joinpath("saved")

    saved_paths = save_fonts_at_commit([fonts_path], "HEAD", output_path)

    assert len(saved_paths) == 1
    saved_folder = saved_paths[0]
    assert saved_folder.parts[-2:] == ("fonts", "ttf")
    # Every font in the folder at the commit, but not other files
    assert sorted(path.name for path in saved_folder.iterdir()) == [
        "Test-Bold.ttf",
        "Test-Regular.ttf",
        "Test-Removed.ttf",
    ]
    assert glyph_count(saved_folder / "Test-Regular.ttf") == len(GLYPH_ORDER) - 1

    # An earlier commit, by tag
    first_paths = save_fonts_at_commit([fonts_path], "first", tmp_path / "first")
    assert glyph_count(first_paths[0] / "Test-Regular.ttf") == len(GLYPH_ORDER)


def test_save_fonts_at_commit_fonts(repo, tmp_path):
    fonts_path = repo.joinpath("fonts", "ttf")
    # A font that wasn't in the commit isn't saved
    saved_paths = save_fonts_at_commit(
        [fonts_path / "Test-Regular.ttf", fonts_path / "Test-Added.ttf"],
        "HEAD~1",
        tmp_path / "saved",
    )
    assert [path.name for path in saved_paths] == ["Test-Regular.ttf"]
    assert saved_paths[0].is_file()
    assert glyph_count(saved_paths[0]) == len(GLYPH_ORDER)


def test_save_fonts_at_commit_errors(repo, tmp_path):
    fonts_path = repo.joinpath("fonts", "ttf")
    with pytest.raises(ValueError, match="missing isn't a commit"):
        save_fonts_at_commit([fonts_path], "missing", tmp_path / "saved")
    with pytest.raises(FileNotFoundError, match="not found"):
        save_fonts_at_commit([fonts_path / "Missing.ttf"], "HEAD", tmp_path / "saved")
    outside_path = tmp_path.joinpath("outside")
    outside_path.mkdir()
    with pytest.raises(ValueError, match="isn't in a git repository"):
        save_fonts_at_commit([outside_path], "HEAD", tmp_path / "saved")


def test_main_commit(repo, tmp_path, capsys):
    fonts_path = repo.joinpath("fonts", "ttf")
    output_path = tmp_path.joinpath("out")
    assert main([str(fonts_path), "--commit", "-o", str(output_path)]) == 0
    out, err = capsys.readouterr()
    pages = [
        output_path.joinpath("Test-Bold-hinting.html"),
        output_path.joinpath("Test-Regular-hinting.html"),
        output_path.joinpath("index.html"),
    ]
    assert out == "".join(f"{path}\n" for path in pages)
    assert "Test-Removed.ttf was in HEAD but isn't now, so it's skipped" in err
    assert f"{fonts_path / 'Test-Added.ttf'} wasn't in HEAD, so it's skipped" in err
    # The old font is from the commit, saved before the temporary folder went
    assert glyph_count(output_path / "hinting-old-Test-Regular.ttf") == (
        len(GLYPH_ORDER) - 1
    )
    assert glyph_count(output_path / "hinting-new-Test-Regular.ttf") == (
        len(GLYPH_ORDER) - 2
    )


def test_main_commit_ref_and_fonts(repo, tmp_path, capsys):
    fonts_path = repo.joinpath("fonts", "ttf")
    output_path = tmp_path.joinpath("out")
    args = ["-fa", str(fonts_path / "Test-Regular.ttf"), "-o", str(output_path)]
    assert main([*args, "--commit", "first"]) == 0
    assert capsys.readouterr().out == (
        f"{output_path.joinpath('Test-Regular-hinting.html')}\n"
    )
    assert glyph_count(output_path / "hinting-old-Test-Regular.ttf") == len(GLYPH_ORDER)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--commit"], "the new fonts are needed"),
        (["--commit", "-fb", "a.ttf"], "not -fb"),
        (["--commit", "missing"], "missing isn't a commit"),
        (["--commit", "HEAD", "Test-Added.ttf"], "none of the fonts were in HEAD"),
    ],
)
def test_main_commit_errors(repo, args, message, monkeypatch, capsys):
    monkeypatch.chdir(repo.joinpath("fonts", "ttf"))
    if "missing" in args:
        args = ["Test-Regular.ttf", *args]
    with pytest.raises(SystemExit) as exit_info:
        main(args)
    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err


def test_main_commit_taken_as_folder(repo, monkeypatch, capsys):
    # The folder is taken as the commit
    monkeypatch.chdir(repo)
    with pytest.raises(SystemExit):
        main(["--commit", "fonts"])
    assert "fonts was taken as the commit" in capsys.readouterr().err
