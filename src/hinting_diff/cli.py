import argparse
import sys
from pathlib import Path

from hinting_diff import __version__
from hinting_diff.page import write_hinting_page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hinting-diff",
        description=(
            "Write a page to compare the TrueType hinting of two versions of a "
            "font. Browsers only apply TrueType hinting on Windows, so open the "
            "page on Windows."
        ),
    )
    parser.add_argument("before", type=Path, help="the old font (TTF)")
    parser.add_argument("after", type=Path, help="the new font (TTF)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("hinting-diff"),
        help="folder for the page and copies of the fonts (default: hinting-diff)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    for font_path in (args.before, args.after):
        if not font_path.is_file():
            parser.error(f"{font_path} not found")
    try:
        page_path = write_hinting_page(args.before, args.after, args.output)
    except Exception as error:  # noqa: BLE001
        print(f"hinting-diff: error: {error}", file=sys.stderr)
        return 1
    print(page_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
