import pytest

from hinting_diff import __version__
from hinting_diff.cli import main


def test_main(font_path, tmp_path, capsys):
    output_path = tmp_path.joinpath("out")
    assert main([str(font_path), str(font_path), "-o", str(output_path)]) == 0
    page_path = output_path.joinpath("Test-Regular-hinting.html")
    assert page_path.is_file()
    assert capsys.readouterr().out == f"{page_path}\n"


def test_main_default_output(font_path, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main([str(font_path), str(font_path)]) == 0
    assert tmp_path.joinpath("hinting-diff", "Test-Regular-hinting.html").is_file()


def test_main_missing_font(font_path, tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([str(font_path), str(tmp_path.joinpath("missing.ttf"))])
    assert exit_info.value.code == 2
    assert "missing.ttf not found" in capsys.readouterr().err


def test_main_bad_font(font_path, tmp_path, capsys):
    bad_path = tmp_path.joinpath("bad.ttf")
    bad_path.write_bytes(b"not a font")
    assert main([str(bad_path), str(font_path), "-o", str(tmp_path)]) == 1
    assert capsys.readouterr().err.startswith("hinting-diff: error: ")


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out == f"{__version__}\n"


@pytest.fixture
def families(font_factory, tmp_path):
    """Old and new folders of fonts, with a font removed and one added."""
    for name in ("Test-Regular.ttf", "Test-Bold.ttf", "Test-Removed.ttf"):
        font_factory(f"old/{name}")
    for name in ("Test-Regular.ttf", "Test-Bold.ttf", "Test-Added.ttf"):
        font_factory(f"new/{name}")
    return tmp_path.joinpath("fonts", "old"), tmp_path.joinpath("fonts", "new")


def check_family_output(output_path, capsys):
    pages = [
        output_path.joinpath("Test-Bold-hinting.html"),
        output_path.joinpath("Test-Regular-hinting.html"),
    ]
    index_path = output_path.joinpath("index.html")
    for path in (*pages, index_path):
        assert path.is_file()
    assert not output_path.joinpath("Test-Added-hinting.html").exists()
    out, err = capsys.readouterr()
    assert out == "".join(f"{path}\n" for path in (*pages, index_path))
    assert "Test-Removed.ttf has no new font with the same name" in err
    assert "Test-Added.ttf has no old font with the same name" in err


def test_main_folders(families, tmp_path, capsys):
    output_path = tmp_path.joinpath("out")
    before_path, after_path = families
    assert main([str(before_path), str(after_path), "--out", str(output_path)]) == 0
    check_family_output(output_path, capsys)


def test_main_fonts_before_after(families, tmp_path, capsys):
    output_path = tmp_path.joinpath("out")
    before_path, after_path = families
    # As a shell would expand `old/*.ttf new/*.ttf`
    assert (
        main(
            [
                "-fb",
                *map(str, sorted(before_path.glob("*.ttf"))),
                "-fa",
                *map(str, sorted(after_path.glob("*.ttf"))),
                "-o",
                str(output_path),
            ]
        )
        == 0
    )
    check_family_output(output_path, capsys)


def test_main_bad_font_in_family(families, tmp_path, capsys):
    # The other fonts' pages are still written
    before_path, after_path = families
    after_path.joinpath("Test-Bold.ttf").write_bytes(b"not a font")
    output_path = tmp_path.joinpath("out")
    assert (
        main(["-fb", str(before_path), "-fa", str(after_path), "-o", str(output_path)])
        == 1
    )
    out, err = capsys.readouterr()
    assert out == f"{output_path.joinpath('Test-Regular-hinting.html')}\n"
    assert "hinting-diff: error: Test-Bold.ttf: " in err
    assert not output_path.joinpath("index.html").exists()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "the old and the new fonts are needed"),
        (["a.ttf"], "give one old and one new font or folder"),
        # The command in issue #4
        (["a.ttf", "b.ttf", "c.ttf", "d.ttf"], "-fb old/*.ttf -fa new/*.ttf"),
        (["-fb", "a.ttf"], "the old and the new fonts are needed"),
        (["a.ttf", "b.ttf", "-fb", "c.ttf"], "not both"),
    ],
)
def test_main_argument_errors(args, message, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(args)
    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err


def test_main_no_matches(font_factory, tmp_path, capsys):
    font_factory("old/Test-Regular.ttf")
    font_factory("new/Test-Bold.ttf")
    fonts_path = tmp_path.joinpath("fonts")
    with pytest.raises(SystemExit) as exit_info:
        main([str(fonts_path / "old"), str(fonts_path / "new")])
    assert exit_info.value.code == 2
    assert "none of the old and new fonts have the same file names" in (
        capsys.readouterr().err
    )


def test_main_empty_folder(font_path, tmp_path, capsys):
    empty_path = tmp_path.joinpath("empty")
    empty_path.mkdir()
    with pytest.raises(SystemExit):
        main([str(empty_path), str(font_path)])
    assert f"no TrueType fonts (.ttf) in {empty_path}" in capsys.readouterr().err
