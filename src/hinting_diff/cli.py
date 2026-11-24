import argparse
import sys
import tempfile
from pathlib import Path

from hinting_diff import __version__
from hinting_diff.git import save_fonts_at_commit
from hinting_diff.matching import match_fonts
from hinting_diff.page import write_hinting_page, write_index_page

_USAGE = """
  %(prog)s [-h] [-o OUT] [--version] BEFORE AFTER
  %(prog)s [-h] [-o OUT] [--version] -fb FONT [FONT ...] -fa FONT [FONT ...]
  %(prog)s [-h] [-o OUT] [--version] AFTER [AFTER ...] --commit [REF]"""


def _warn(message: str) -> None:
    print(f"hinting-diff: warning: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hinting-diff",
        usage=_USAGE,
        description=(
            "Write pages to compare the TrueType hinting of two versions of fonts. "
            "Give the old and new font, or folders of them, or several fonts with "
            "-fb and -fa: fonts are matched by their file names. Or give the new "
            "fonts, or folders of them, in a git repository, with --commit to compare "
            "them with the fonts at the same paths in a commit. Browsers only apply "
            "TrueType hinting on Windows, so open the pages on Windows."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="BEFORE AFTER",
        help="the old and the new font (TTF), or folders of fonts. With --commit, "
        "the new fonts or folders",
    )
    parser.add_argument(
        "-fb",
        "--fonts-before",
        nargs="+",
        type=Path,
        default=[],
        metavar="FONT",
        help="the old fonts (TTF), or folders of fonts",
    )
    parser.add_argument(
        "-fa",
        "--fonts-after",
        nargs="+",
        type=Path,
        default=[],
        metavar="FONT",
        help="the new fonts (TTF), or folders of fonts",
    )
    parser.add_argument(
        "--commit",
        nargs="?",
        const="HEAD",
        metavar="REF",
        help="compare the new fonts with the fonts at the same paths in this commit, "
        "e.g. HEAD~1 or a tag (default: HEAD, the last commit)",
    )
    parser.add_argument(
        "-o",
        "--out",
        "--output",
        dest="output",
        metavar="OUT",
        type=Path,
        default=Path("hinting-diff"),
        help="folder for the pages and copies of the fonts (default: hinting-diff)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.commit is not None:
        if args.fonts_before:
            parser.error("give the new fonts with --commit, not -fb")
        after_paths = [*args.paths, *args.fonts_after]
        if not after_paths:
            # e.g. `--commit fonts/`, where the folder is taken as the commit
            if Path(args.commit).exists():
                parser.error(
                    f"{args.commit} was taken as the commit: give the fonts before "
                    f"--commit, e.g. {args.commit} --commit"
                )
            parser.error("the new fonts are needed")
        with tempfile.TemporaryDirectory() as temp_folder:
            try:
                before_paths = save_fonts_at_commit(
                    after_paths, args.commit, Path(temp_folder)
                )
            except (FileNotFoundError, ValueError) as error:
                parser.error(str(error))
            return _write_pages(
                parser, before_paths, after_paths, args.output, args.commit
            )
    if args.paths:
        if args.fonts_before or args.fonts_after:
            parser.error("give BEFORE AFTER or -fb and -fa, not both")
        if len(args.paths) != 2:
            parser.error(
                "give one old and one new font or folder, or several fonts with "
                "-fb and -fa, e.g. -fb old/*.ttf -fa new/*.ttf"
            )
        before_paths, after_paths = [args.paths[0]], [args.paths[1]]
    elif args.fonts_before and args.fonts_after:
        before_paths, after_paths = args.fonts_before, args.fonts_after
    else:
        parser.error("the old and the new fonts are needed")
    return _write_pages(parser, before_paths, after_paths, args.output)


def _write_pages(
    parser: argparse.ArgumentParser,
    before_paths: list[Path],
    after_paths: list[Path],
    output_path: Path,
    commit: str | None = None,
) -> int:
    """
    Writes a page for each old and new font with the same name, and an index page
    if there are several. Returns the command's exit code.
    """
    try:
        font_match = match_fonts(before_paths, after_paths)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    if commit is None:
        for before_path in font_match.only_before:
            _warn(f"{before_path} has no new font with the same name, so it's skipped")
        for after_path in font_match.only_after:
            _warn(f"{after_path} has no old font with the same name, so it's skipped")
        if not font_match.pairs:
            parser.error("none of the old and new fonts have the same file names")
    else:
        for before_path in font_match.only_before:
            _warn(f"{before_path.name} was in {commit} but isn't now, so it's skipped")
        for after_path in font_match.only_after:
            _warn(f"{after_path} wasn't in {commit}, so it's skipped")
        if not font_match.pairs:
            parser.error(f"none of the fonts were in {commit}")

    # A font that can't be read doesn't stop the other fonts' pages
    page_paths: list[Path] = []
    for before_path, after_path in font_match.pairs:
        try:
            page_paths.append(write_hinting_page(before_path, after_path, output_path))
        except Exception as error:  # noqa: BLE001
            print(f"hinting-diff: error: {after_path.name}: {error}", file=sys.stderr)
        else:
            print(page_paths[-1])
    if len(page_paths) > 1:
        print(write_index_page(page_paths, output_path))
    return 0 if len(page_paths) == len(font_match.pairs) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
