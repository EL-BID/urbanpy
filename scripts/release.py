"""Validate immutable UrbanPy release inputs without mutating source files."""

from __future__ import annotations

import argparse
import email.parser
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

from packaging.version import Version


class ReleaseValidationError(ValueError):
    """A release input is inconsistent or unsafe to publish."""


def project_version(pyproject: Path = Path("pyproject.toml")) -> Version:
    with pyproject.open("rb") as source:
        value = tomllib.load(source)["project"]["version"]
    return Version(value)


def validate_tag(tag: str, *, pyproject: Path = Path("pyproject.toml")) -> Version:
    if not tag.startswith("v"):
        raise ReleaseValidationError("release tags must start with 'v'")
    tagged = Version(tag[1:])
    declared = project_version(pyproject)
    if tagged != declared:
        raise ReleaseValidationError(
            f"tag version {tagged} does not match project version {declared}"
        )
    return declared


def validate_artifacts(directory: Path, expected: Version) -> None:
    wheels = sorted(directory.glob("urbanpy-*.whl"))
    sdists = sorted(directory.glob("urbanpy-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseValidationError("expected exactly one UrbanPy wheel and one sdist")
    wheel_version = _wheel_version(wheels[0])
    sdist_version = _sdist_version(sdists[0])
    if wheel_version != expected or sdist_version != expected:
        raise ReleaseValidationError(
            "wheel, sdist, and requested release versions must match"
        )


def validate_target(version: Version, target: str) -> None:
    if target not in {"pypi", "testpypi"}:
        raise ReleaseValidationError("target must be pypi or testpypi")
    if target == "pypi" and (version.is_prerelease or version.is_devrelease):
        raise ReleaseValidationError("prereleases must be exercised on TestPyPI")


def _wheel_version(path: Path) -> Version:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ReleaseValidationError("wheel must contain exactly one METADATA file")
        message = email.parser.BytesParser().parsebytes(archive.read(metadata_names[0]))
    if message.get("Name") != "urbanpy":
        raise ReleaseValidationError("wheel project name is not urbanpy")
    return Version(message["Version"])


def _sdist_version(path: Path) -> Version:
    with tarfile.open(path, "r:gz") as archive:
        roots = {name.split("/", 1)[0] for name in archive.getnames() if name}
    if len(roots) != 1:
        raise ReleaseValidationError("sdist must contain exactly one root directory")
    root = roots.pop()
    prefix = "urbanpy-"
    if not root.startswith(prefix):
        raise ReleaseValidationError("sdist root must use the UrbanPy project name")
    return Version(root.removeprefix(prefix))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--target", choices=("pypi", "testpypi"))
    args = parser.parse_args(argv)
    try:
        version = validate_tag(args.tag)
        if args.artifacts:
            validate_artifacts(args.artifacts, version)
        if args.target:
            validate_target(version, args.target)
    except (ReleaseValidationError, OSError, KeyError) as error:
        print(f"release validation failed: {error}", file=sys.stderr)
        return 2
    print(f"validated UrbanPy {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
