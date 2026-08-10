# UrbanPy agent instructions

UrbanPy is a geospatial Python library maintained by EL-BID. Treat every change
as public, long-lived library code.

## Environment and validation

- Use Python 3.11 as the development baseline and preserve support through the
  versions listed in `pyproject.toml`.
- Install with `uv sync --locked --all-groups`. Change dependencies in
  `pyproject.toml`, then refresh and commit `uv.lock`.
- Run `uv run pytest` for the default hermetic suite. Network access is disabled
  by default. Mark real provider checks `live` and Docker checks `docker`; never
  make either a normal PR prerequisite.
- Run `trunk check` on changed files. The direct, authoritative fallbacks are
  `uv run ruff check urbanpy tests`, `uv run pytest`, `uv build`, and
  `uv run sphinx-build --fail-on-warning --keep-going -b html docs/source docs/_build/html`.
- SonarQube is an EL-BID requirement. Never bypass, remove, soften, or mark its
  tests, coverage generation, scanner, or quality gate as best effort.

## Engineering boundaries

- Keep public API changes backward compatible unless an issue and changelog
  explicitly identify a breaking change.
- Validate external data at I/O boundaries. Pydantic models represent request,
  response, and configuration contracts—not individual GeoDataFrame rows.
- Resolve Geofabrik extracts from `index-v1-nogeom.json`; canonical IDs and the
  advertised PBF URL are authoritative. Do not construct URLs from guessed
  continent/country strings.
- Keep OSRM HTTP client code separate from local Docker lifecycle code. New
  lifecycle logic must be Python, cross-platform, explicit about timeouts, and
  safe under concurrent runs. Do not add shell orchestration.
- Tests use synthetic geometry or captured provider payloads. Never depend on
  mutable live data for a unit assertion.

## Pull-request discipline

- Work from a focused issue with acceptance criteria and declare dependencies.
- Prefer a small PR or a dependency-ordered stacked PR. Do not mix formatting,
  generated files, and behavioral changes without a clear reason.
- Never commit credentials, provider keys, real user email addresses, or data
  that cannot be redistributed.
- Pin third-party GitHub Actions to immutable commit SHAs and retain the version
  tag in a comment.
- Agents may open issues and PRs, but must not merge, release, change repository
  secrets, weaken branch protection, or dismiss security/license findings.
  Escalate those decisions to a maintainer.
