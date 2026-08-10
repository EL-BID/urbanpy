# Contributing to UrbanPy

Thank you for helping UrbanPy become a dependable geospatial library. Please
follow the [code of conduct](CODE_OF_CONDUCT.md) in every project interaction.

## Propose the change

Search existing issues first. Bugs should include a minimal reproduction,
UrbanPy/Python versions, CRS and data details, and redacted logs. Larger changes
need an issue with explicit scope, acceptance criteria, dependencies, and public
API implications before implementation begins.

## Set up development

Install [uv](https://docs.astral.sh/uv/), clone the repository, then run:

```console
uv sync --locked --all-groups
uv run pytest
```

Python 3.11 is the local baseline. The supported range is declared in
`pyproject.toml` and exercised in CI. The committed `uv.lock` is authoritative
for development and CI; published users receive the bounded dependencies from
`pyproject.toml`.

Trunk provides one convenient frontend for repository checks:

```console
trunk check
```

Trunk does not replace the underlying commands. When it is unavailable, run:

```console
uv run ruff check urbanpy tests
uv run pytest
uv build
uv run sphinx-build --fail-on-warning --keep-going -b html docs/source docs/_build/html
```

## Test policy

The normal test suite is deterministic and disables network sockets. Use
synthetic geometries and captured provider payloads for unit and contract tests.
Tests that intentionally call a real provider must use `@pytest.mark.live`;
tests requiring Docker must use `@pytest.mark.docker`. Run those suites only in
an explicitly prepared environment:

```console
uv run pytest -o addopts="" -m live tests/live_provider_test.py
uv run pytest -o addopts="" -m docker tests/osrm_docker_test.py
```

Never place credentials or personal email addresses in tests or fixtures.

## Pull requests

Keep pull requests focused and link the issue they implement. Dependency-ordered
stacked PRs are welcome when each layer is independently reviewable; identify
the base and next PR in every description. Add regression tests for fixes and
documentation/changelog entries for user-visible behavior.

All required checks must pass. SonarQube is mandatory under EL-BID policy and
must not be removed, bypassed, or converted to a best-effort check. A maintainer
reviews and merges changes; automation and coding agents never merge or release
on their own.
