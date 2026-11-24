"""
Reads the old versions of fonts from a commit in their git repository, to compare
them with the fonts as they are now.
"""

import subprocess
from collections.abc import Iterable
from pathlib import Path


def _git(repo_path: Path, *args: str) -> bytes:
    """Runs a git command in a folder, and returns its output."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise ValueError("git isn't installed") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode(errors="replace").strip()
        raise ValueError(message or f"git {args[0]} failed") from error
    return result.stdout


def _repo_root(path: Path) -> Path:
    folder_path = path if path.is_dir() else path.parent
    try:
        root = _git(folder_path, "rev-parse", "--show-toplevel")
    except ValueError as error:
        raise ValueError(f"{path} isn't in a git repository") from error
    return Path(root.decode().strip()).resolve()


def save_fonts_at_commit(
    paths: Iterable[Path], commit: str, output_path: Path
) -> list[Path]:
    """
    Saves the fonts in `paths` as they were at a commit (e.g. "HEAD", "HEAD~1", a
    tag or a commit hash) in `output_path`, and returns their paths there, to
    compare with the fonts in `paths` (see `match_fonts()`). Each path is a font or
    a folder of fonts in a git repository: for a folder, every TrueType font (.ttf)
    that was in it, or its subfolders, at the commit is saved. A font that wasn't in
    the commit isn't saved. Raises `ValueError` if a path isn't in a git repository
    or the commit doesn't exist.
    """
    saved_paths: list[Path] = []
    # A folder for each repository, in case two have files at the same path
    repo_folders: dict[Path, Path] = {}
    commit_hashes: dict[Path, str] = {}
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        root = _repo_root(path)
        if root not in repo_folders:
            repo_folders[root] = output_path.joinpath(str(len(repo_folders)))
            try:
                commit_hashes[root] = (
                    _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
                    .decode()
                    .strip()
                )
            except ValueError as error:
                raise ValueError(f"{commit} isn't a commit in {root}") from error
        commit_hash = commit_hashes[root]
        relative_path = path.resolve().relative_to(root).as_posix()
        # The files in the folder at the commit, or just the font
        files = [
            name
            for name in _git(
                root,
                "ls-tree",
                "-r",
                "-z",
                "--name-only",
                commit_hash,
                "--",
                relative_path,
            )
            .decode()
            .split("\0")
            if name and (path.is_file() or name.lower().endswith(".ttf"))
        ]
        if path.is_file():
            # `ls-tree` lists a folder's files when it's given its path
            files = [name for name in files if name == relative_path]
        for name in files:
            saved_path = repo_folders[root].joinpath(name)
            saved_path.parent.mkdir(parents=True, exist_ok=True)
            # With git's filters, e.g. so Git LFS gives the font, not its pointer
            saved_path.write_bytes(
                _git(root, "cat-file", "--filters", f"{commit_hash}:{name}")
            )
        if files:
            saved_paths.append(repo_folders[root].joinpath(relative_path))
    return saved_paths
