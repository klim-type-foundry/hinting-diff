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
