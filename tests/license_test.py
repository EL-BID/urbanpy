from pathlib import Path

from packaging.utils import canonicalize_name

from scripts.check_licenses import audit, observed_license, runtime_closure


def test_runtime_dependency_closure_has_an_approved_license_disposition():
    report, violations = audit(Path("license-policy.toml"))

    assert not violations
    assert report
    assert report == sorted(report, key=lambda item: canonicalize_name(item["name"]))
    assert all(item["approved"] for item in report)
    assert {item["name"].casefold() for item in report} >= {
        "geopandas",
        "h3",
        "osmnx",
        "pydantic",
        "urbanpy",
    }


def test_runtime_closure_excludes_development_only_packages():
    names = {item.metadata["Name"].casefold() for item in runtime_closure()}

    assert "pytest" not in names
    assert "sphinx" not in names


def test_every_runtime_distribution_exposes_or_has_a_reviewed_license():
    observed = {
        item.metadata["Name"]: observed_license(item) for item in runtime_closure()
    }

    assert observed["urbanpy"] == "GPL-3.0-only"
    assert observed["defopt"] == "UNKNOWN"
