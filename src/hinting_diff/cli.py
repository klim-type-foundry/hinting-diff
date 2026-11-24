import argparse
import sys
from pathlib import Path

from hinting_diff import __version__
from hinting_diff.matching import match_fonts
from hinting_diff.page import write_hinting_page, write_index_page

_USAGE = """
  %(prog)s [-h] [-o OUT] [--version] BEFORE AFTER
  %(prog)s [-h] [-o OUT] [--version] -fb FONT [FONT ...] -fa FONT [FONT ...]"""


def _warn(message: str) -> None:
    print(f"hinting-diff: warning: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hinting-diff",
        usage=_USAGE,
        description=(
            "Write pages to compare the TrueType hinting of two versions of fonts. "
            "Give the old and new font, or folders of them, or several fonts with "
            "-fb and -fa: fonts are matched by their file names. Browsers only "
            "apply TrueType hinting on Windows, so open the pages on Windows."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="BEFORE AFTER",
        help="the old and the new font (TTF), or folders of fonts",
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

    try:
        font_match = match_fonts(before_paths, after_paths)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    for before_path in font_match.only_before:
        _warn(f"{before_path} has no new font with the same name, so it's skipped")
    for after_path in font_match.only_after:
        _warn(f"{after_path} has no old font with the same name, so it's skipped")
    if not font_match.pairs:
        parser.error("none of the old and new fonts have the same file names")

    # A font that can't be read doesn't stop the other fonts' pages
    page_paths: list[Path] = []
    for before_path, after_path in font_match.pairs:
        try:
            page_paths.append(write_hinting_page(before_path, after_path, args.output))
        except Exception as error:  # noqa: BLE001
            print(f"hinting-diff: error: {after_path.name}: {error}", file=sys.stderr)
        else:
            print(page_paths[-1])
    if len(page_paths) > 1:
        print(write_index_page(page_paths, args.output))
    return 0 if len(page_paths) == len(font_match.pairs) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
