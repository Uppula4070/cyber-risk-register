from pathlib import Path

import pytest
import yaml

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample-co" / "risks.yaml"


@pytest.fixture
def sample() -> Path:
    return SAMPLE


@pytest.fixture
def edit_register(tmp_path):
    """Copy the sample register, let a test change it, and return the new file's path."""

    def _edit(change) -> Path:
        data = yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))
        change(data)
        path = tmp_path / "risks.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    return _edit
