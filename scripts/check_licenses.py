"""Audit installed UrbanPy runtime dependency license metadata."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import tomllib
from collections import deque
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def runtime_closure(root: str = "urbanpy") -> list[importlib.metadata.Distribution]:
    installed = {
        canonicalize_name(dist.metadata["Name"]): dist
        for dist in importlib.metadata.distributions()
        if dist.metadata.get("Name")
    }
    pending = deque([canonicalize_name(root)])
    visited: set[str] = set()
    result: list[importlib.metadata.Distribution] = []
    environment = default_environment() | {"extra": ""}
    while pending:
        name = pending.popleft()
        if name in visited:
            continue
        visited.add(name)
        distribution = installed.get(name)
        if distribution is None:
            raise ValueError(f"runtime dependency {name!r} is not installed")
        result.append(distribution)
        for value in distribution.requires or ():
            requirement = Requirement(value)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            pending.append(canonicalize_name(requirement.name))
    return sorted(result, key=lambda item: canonicalize_name(item.metadata["Name"]))


def observed_license(distribution: importlib.metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression.strip()
    classifiers = sorted(
        {
            value.rsplit(" :: ", 1)[-1].strip()
            for value in distribution.metadata.get_all("Classifier", [])
            if value.startswith("License :: ")
        }
    )
    if classifiers:
        return "; ".join(classifiers)
    value = distribution.metadata.get("License")
    return value.strip() if value and value.strip() else "UNKNOWN"


def audit(policy_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with policy_path.open("rb") as source:
        policy = tomllib.load(source)
    allowed = set(policy["policy"]["allowed"])
    overrides = {
        canonicalize_name(name): value
        for name, value in policy.get("packages", {}).items()
    }
    report: list[dict[str, Any]] = []
    violations: list[str] = []
    for distribution in runtime_closure():
        name = distribution.metadata["Name"]
        observed = observed_license(distribution)
        override = overrides.get(canonicalize_name(name))
        effective = override["license"] if override else observed
        approved = effective in allowed
        record = {
            "approved": approved,
            "effective_license": effective,
            "name": name,
            "observed_license": observed,
            "version": distribution.version,
        }
        if override:
            record["disposition"] = override["disposition"]
            record["source"] = override["source"]
        report.append(record)
        if not approved:
            violations.append(f"{name} {distribution.version}: {observed}")
    return report, violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("license-policy.toml"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report, violations = audit(args.policy)
    except (OSError, KeyError, ValueError) as error:
        print(f"license audit failed: {error}", file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if violations:
        print("unapproved runtime dependency licenses:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print(f"approved {len(report)} runtime package license records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
