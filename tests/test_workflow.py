import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_screenshots_workflow_installs_this_release():
    # The reusable workflow installs the release it's from, so callers that pin it
    # to a release's tag get the same release of the package
    workflow = ROOT.joinpath(".github", "workflows", "screenshots.yml").read_text()
    default = re.search(r"default: 'hinting-diff\[screenshot\]==([^']+)'", workflow)
    assert default is not None
    assert default[1] == ROOT.joinpath("VERSION").read_text().strip()
