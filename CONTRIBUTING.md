# Contributing

Thanks for helping to improve hinting-diff! Bug reports, ideas and pull requests
are all welcome.

## Reporting a bug or asking for a feature

[Open an issue](https://github.com/klim-type-foundry/hinting-diff/issues/new/choose)
and pick the form that fits. For a bug, it helps to know:

- the hinting-diff version (`hinting-diff --version`)
- your operating system, and the browser and operating system you opened the
  page on
- the command you ran, or the Python code you used
- what you expected, and what happened instead (a screenshot of the page helps
  a lot)

If you can share the fonts, or a smaller font that shows the same problem,
please do. If you can't share them, say so, and we'll work out another way.

Please report security problems privately, not in an issue: see
[SECURITY.md](SECURITY.md).

## Making a change

For anything bigger than a small fix, please open an issue first, so we can
agree on the approach before you spend time on it.

### Setting up

With [uv](https://docs.astral.sh/uv/) installed:

```shell
make init
```

This sets up the Python environment in `.venv/` with the exact package versions
from `uv.lock`, and installs the [pre-commit](https://pre-commit.com/) hooks.

### Checks

```shell
make test
```

Before each commit, the pre-commit hooks run Ruff (linting and formatting), mypy
and some general file checks. The same checks and the tests run on every pull
request.

- **Tests:** add or update tests in `tests/` for what you change.
- **Types:** the code is fully type-annotated, and mypy must pass with no errors.
- **Documentation:** if you change the command's options or the Python API,
  update the [README](README.md) too.
- **Browsers:** if you change the page, check it in a browser on Windows, as
  that's the only platform where browsers apply TrueType hinting.

### Pull requests

- Keep each pull request to one change, and describe what it changes and why.
- Pull requests are squash-merged, so the pull request's title becomes the
  commit message on `main`: write it as a short summary of the change, e.g.
  "Show the glyph's Unicode value on hover".
- Don't change `VERSION`: the maintainers do that when releasing.

## Releasing (maintainers)

To release a new version, change the version in `VERSION` and merge it into
`main`. The release workflow runs the checks, builds the package, publishes it
to [PyPI](https://pypi.org/project/hinting-diff/), and then creates a GitHub
release tagged with the version (e.g. `v0.1.0`), with the package's files
attached.

The workflow publishes to PyPI with
[trusted publishing](https://docs.pypi.org/trusted-publishers/), so there's no
PyPI token to manage. PyPI only accepts uploads from `release.yml` in the
`pypi` environment, which can only be used from `main`.

## Licence

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE.txt), the same as the rest of the project.

## Code of conduct

This project follows a [code of conduct](CODE_OF_CONDUCT.md). By taking part,
you agree to follow it.
