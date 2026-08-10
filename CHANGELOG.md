# Changelog

All notable user-visible changes are recorded here. UrbanPy follows semantic
versioning and uses the headings from [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- A uv-managed PEP 621 build with a reproducible development lockfile and Python
  3.11–3.14 CI matrix.
- Strict Pydantic boundary models for coordinates, bounding boxes, travel
  profiles, Geofabrik records, and the OSRM lifecycle.
- Canonical Geofabrik catalog resolution using official IDs, exact ISO aliases,
  and provider-advertised PBF URLs.
- A cross-platform Python OSRM manager with atomic downloads/preparation,
  pinned containers, ownership protection, readiness checks, and dry-run cleanup.
- A Docker-independent typed OSRM route/table client.
- Hermetic provider contract tests, mandatory SonarQube enforcement, Trunk code
  quality, dependency auditing, and agent governance.
- A shared identified HTTP session with bounded safe retries and explicit
  connect/read timeouts for provider clients.
- Protected OIDC publishing workflows that build once, validate artifacts,
  generate dependency/SBOM evidence, attest provenance, and promote the same
  reviewed bundle to TestPyPI or PyPI.
- Public API stability documentation, explicit module exports, dependency-license
  evidence, and advisory AI-review policy for stacked pull requests.

### Changed

- H3 4.x, OSMnx 2.x, GeoPandas 1.x, and current HDX behavior are supported and
  regression-tested.
- OSRM durations are documented in seconds, matching the upstream API.
- Geospatial outputs retain their input or declared CRS in the corrected paths.
- HDX searches use the current client and return stable UrbanPy provider errors.
- Overpass POI bounds are validated as WGS84 ``(west, south, east, north)``
  values through the public ``BoundingBox`` contract.
- Plotly choropleths use the current MapLibre-backed trace instead of the
  deprecated Mapbox trace.

### Fixed

- `merge_shape_hex` can be rerun on its own result.
- One-resource HDX selections no longer pass a pandas Series to `read_csv`.
- OSMnx nearest-node coordinate order and graph isochrone coordinate fields.
- OSRM nested Geofabrik regions, platform divergence, false readiness, unsafe
  container collisions, partial downloads, and incorrect MLD path extensions.

### Deprecated

- `start_osrm_server` and `stop_osrm_server`; migrate to `OSRMConfig` and
  `OSRMManager` before the next breaking release.

### Removed

- The unsupported OSRM Bash, PowerShell, legacy class, and notebook launchers.

## [0.2.2] - 2024-07-18

The historical release predates the structured changelog. See the
[GitHub release](https://github.com/EL-BID/urbanpy/releases/tag/v0.2.2).

[Unreleased]: https://github.com/EL-BID/urbanpy/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/EL-BID/urbanpy/releases/tag/v0.2.2
