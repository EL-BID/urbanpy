import tarfile
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version

from scripts.release import (
    ReleaseValidationError,
    validate_artifacts,
    validate_tag,
    validate_target,
)


def _pyproject(path: Path, version: str) -> Path:
    path.write_text(f'[project]\nname = "urbanpy"\nversion = "{version}"\n')
    return path


def test_tag_must_exactly_match_declared_version(tmp_path):
    pyproject = _pyproject(tmp_path / "pyproject.toml", "0.3.0a1")

    assert validate_tag("v0.3.0a1", pyproject=pyproject) == Version("0.3.0a1")
    with pytest.raises(ReleaseValidationError, match="does not match"):
        validate_tag("v0.3.0a2", pyproject=pyproject)
    with pytest.raises(ReleaseValidationError, match="start with"):
        validate_tag("0.3.0a1", pyproject=pyproject)


def test_prereleases_cannot_publish_to_production_pypi():
    validate_target(Version("0.3.0a1"), "testpypi")
    validate_target(Version("0.3.0"), "pypi")
    with pytest.raises(ReleaseValidationError, match="TestPyPI"):
        validate_target(Version("0.3.0rc1"), "pypi")


def test_artifact_versions_are_read_from_contents_not_filenames(tmp_path):
    wheel = tmp_path / "urbanpy-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "urbanpy-0.3.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: urbanpy\nVersion: 0.3.0\n",
        )
    sdist = tmp_path / "urbanpy-0.3.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        placeholder = tmp_path / "pyproject.toml"
        placeholder.write_text("[project]\n")
        archive.add(placeholder, arcname="urbanpy-0.3.0/pyproject.toml")

    validate_artifacts(tmp_path, Version("0.3.0"))
    with pytest.raises(ReleaseValidationError, match="must match"):
        validate_artifacts(tmp_path, Version("0.3.1"))
