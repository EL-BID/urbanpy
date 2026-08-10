# OSRM and Geofabrik plan for UrbanPy 0.3

## Outcome

Provide a cross-platform, observable OSRM lifecycle that downloads the correct
Geofabrik extract, prepares it reproducibly, and starts or stops a local service
without embedded Bash or PowerShell implementations.

This epic closes or supersedes issues #21, #26, and #29. It also removes the
duplicate lifecycle implementation in `urbanpy/routing/osrm_routing.py`.

## Current defects to eliminate

- URLs are assembled from `continent` and `country`, which cannot represent the
  Geofabrik hierarchy reliably.
- scripts are not included in installed wheels even though Python calls them;
- Bash and PowerShell implement different paths and behavior;
- the current MLD sequence passes `.osm.pbf` to partition/customize/routed where
  OSRM's prepared `.osrm` dataset base is required;
- the image is floating, processing container names are global, and port 5000 is
  hard-coded;
- slash-containing region IDs are unsafe as filesystem/container names;
- failures are often printed and then reported as success;
- downloads are not atomic or resumable and concurrent preparation is unsafe;
- there is no disk-space preflight, readiness deadline, structured status,
  ownership label, or targeted cleanup policy.

## Architecture decisions

- Python owns orchestration. Shell files, if retained temporarily, only invoke the
  public Python CLI and contain no lifecycle logic.
- Docker commands are argument arrays executed with `shell=False`.
- Use the official OSRM backend image pinned to an explicit supported version and
  record the resolved digest in the preparation manifest. Validate supported CPU
  architectures before selecting the tag.
- Use Geofabrik's `index-v1-nogeom.json` as the catalog and `urls.pbf` verbatim.
  UrbanPy never constructs a PBF URL from region path fragments.
- The exact Geofabrik `properties.id` is canonical, including `/`. ISO 3166-1 and
  ISO 3166-2 codes are lookup aliases. Display names are search text only.
- Silent fuzzy matching is prohibited. Ambiguity raises an error containing
  candidate IDs and parents.
- Store catalog cache, downloaded PBFs, prepared datasets, state, and logs in
  platform-appropriate locations with explicit user overrides.
- Library methods return typed results and raise typed exceptions. Rendering
  progress and messages is a CLI/notebook adapter concern.
- Prepared data is immutable for a specific region, profile, PBF identity, OSRM
  image, and algorithm. Reuse requires an exact manifest match.

## Proposed package layout

The final layout can vary, but responsibilities must remain separated.

```text
urbanpy/
  geofabrik/
    catalog.py       # fetch/cache/index/resolve
    models.py        # internal transport plus public region model
  routing/
    models.py        # OSRM configuration/status/results
    osrm.py          # high-level manager
    osrm_client.py   # route/table HTTP client, independent of Docker
    _docker.py       # injectable command runner
    _download.py     # streamed atomic downloads
    _paths.py        # platform paths and safe resource identifiers
  cli/
    osrm.py          # presentation and exit codes
```

No network, Docker, or filesystem work occurs at import time.

## Public contracts

### Geofabrik catalog

`GeofabrikCatalog` provides:

- `get(region_id)` for an exact canonical ID;
- `resolve(value, parent=None)` with priority exact ID, exact ISO code, then exact
  case-folded display name only when unambiguous;
- `search(text, parent=None)` returning candidates without choosing one;
- `list(parent=None, downloadable_only=True)`;
- `refresh(force=False)` and explicit offline behavior.

`GeofabrikRegion` includes canonical ID, display name, parent ID, ISO aliases,
public PBF URL, and optional ancestry derived from the catalog. It does not expose
the internal-authenticated `pbf-internal` URL.

Catalog validation checks the v1 FeatureCollection envelope, unique IDs, valid
parent references, expected list-valued ISO fields, and HTTPS public URLs. Unknown
third-party fields are tolerated for forward compatibility. The cache honors ETag
and Last-Modified, has an explicit freshness policy, and can fall back to the last
valid copy with a surfaced stale status. Corrupt or partially written catalogs are
never promoted.

### OSRM configuration

`OSRMConfig` contains at least:

- `region_id`;
- `profile`: car, bicycle, or foot;
- `algorithm`: MLD for 0.3;
- host bind address (loopback by default) and host port;
- data/cache path overrides;
- official image reference;
- download, command, and readiness timeouts;
- refresh/rebuild policy;
- optional resource limits supported consistently by Docker.

Profile configuration distinguishes the Lua preparation profile from the OSRM API
profile token. The mapping is explicit and tested.

### OSRM manager

`OSRMManager` provides:

- `plan()` — resolve inputs and return paths, sizes where known, commands, and
  reuse decisions without mutation;
- `prepare()` — download and build a complete prepared dataset;
- `start()` — start or reuse a service and wait for readiness;
- `status()` — return container, manifest, endpoint, and readiness information;
- `stop()` — stop only the matching UrbanPy-owned service;
- `logs()` — stream or read logs without hiding subprocess failures;
- `clean()` — remove explicitly selected UrbanPy-owned containers/artifacts.

The manager is also a context manager. Context exit stops a container it started
but does not delete downloaded or prepared data unless explicitly requested.

### OSRM HTTP client

`OSRMClient` is independent of Docker and accepts any configured OSRM base URL. It
provides typed route/table/nearest operations, explicit timeouts, status/error
translation, response-size limits, and unit-preserving results. Existing routing
functions delegate to this client, which allows the same UrbanPy API to use a
managed local service or an externally operated OSRM endpoint.

## Lifecycle

### 1. Resolve and plan

- Resolve the exact catalog region and use its `urls.pbf`.
- Derive a Docker/filesystem-safe identifier from a readable slug plus a stable
  short hash of the canonical ID. Never use a raw `/` in a resource name.
- Resolve image tag/digest, profile mapping, storage paths, and port.
- Inspect existing manifests and containers through exact labels, not substring
  matches in `docker ps` output.

### 2. Preflight

- Check Docker CLI presence, daemon access, image architecture, writable storage,
  port availability, and a conservative free-space requirement.
- Explain Docker-not-installed, daemon-not-running, permission, port, disk, and
  unsupported-platform errors separately.
- Ask the CLI user to confirm unexpectedly large downloads/processing estimates
  unless a non-interactive confirmation flag is supplied.

### 3. Download

- Stream to a `.part` file with progress, connect/read timeouts, and bounded
  retries.
- Use ETag/Last-Modified and `If-Range` for safe resume when supported. Restart a
  partial download if the remote identity changed.
- Enforce HTTPS, expected Geofabrik public host policy, response-size limits, and
  available disk space.
- Atomically rename only after the response is complete and validation succeeds.
- Record source URL, validators, byte size, retrieval time, and local digest in a
  manifest. Do not claim upstream checksum verification unless an authoritative
  checksum was actually retrieved and verified.

### 4. Prepare

- Acquire a per-dataset inter-process lock.
- Run `osrm-extract` with the selected Lua profile against `.osm.pbf`.
- Run `osrm-partition` and `osrm-customize` against the resulting `.osrm` base.
- Use unique, labeled, automatically removed processing containers so an
  interrupted run cannot collide with another region/profile.
- Capture stdout/stderr to structured logs while preserving live progress.
- Build in a staging directory and atomically publish the complete prepared set
  plus manifest. A failed run never looks reusable.

### 5. Start and verify

- Run a detached, labeled service container with a read-only data mount and the
  selected host bind/port. Bind to `127.0.0.1` by default; external exposure is an
  explicit opt-in with a security warning.
- Use an exact, collision-safe name incorporating region/profile identity.
- Poll until the container is running and the OSRM HTTP endpoint returns a
  well-formed OSRM response, with a deadline and captured diagnostic logs.
- A timeout stops only the container created by that invocation and raises an
  actionable readiness error. No unbounded busy loops or fixed success sleeps.

### 6. Stop and clean

- Find resources by exact UrbanPy ownership/manifest labels.
- `stop()` is idempotent and never removes data.
- `clean()` requires explicit scopes such as container, prepared profile, PBF, or
  catalog cache; dry-run is available and default for broad selections.
- Never remove an unknown container or directory merely because its name contains
  `osrm`.

## Compatibility strategy

For 0.3, current functions remain available:

```python
start_osrm_server(country, continent, profile)
stop_osrm_server(country, continent, profile)
```

They delegate to `OSRMManager`, resolve `country` as an exact catalog ID/alias,
validate legacy continent/path hints against ancestry where possible, and emit a
visible `FutureWarning`. Legacy underscore path workarounds may be recognized only
in this adapter and are never used to construct URLs.

The preferred API is region-centric:

```python
config = OSRMConfig(region_id="us/new-york", profile="foot", port=5001)
with OSRMManager(config) as server:
    result = OSRMClient(server.endpoint).route(origin, destination)
```

If return values or units of `osrm_route`/`compute_osrm_dist_matrix` change, add a
new typed API first and keep legacy tuple/array behavior through the documented
deprecation window.

## CLI

An optional `urbanpy osrm` CLI uses the same manager:

```text
urbanpy osrm regions search new-york
urbanpy osrm plan --region us/new-york --profile foot
urbanpy osrm prepare --region us/new-york --profile foot
urbanpy osrm start --region us/new-york --profile foot --port 5001
urbanpy osrm status --region us/new-york --profile foot
urbanpy osrm logs --region us/new-york --profile foot
urbanpy osrm stop --region us/new-york --profile foot
urbanpy osrm clean --region us/new-york --profile foot --prepared --dry-run
```

Commands support non-interactive operation, machine-readable JSON output, stable
exit codes, Ctrl-C cancellation, and redaction of sensitive environment values.

## GitHub sub-issues

1. Write ADR and public lifecycle/error/compatibility contract.
2. Add Pydantic region/config/status models and safe identifiers.
3. Implement and fixture-test the Geofabrik v1 catalog parser/index.
4. Implement exact ID, ISO, ancestry, search, and ambiguity-aware resolution.
5. Implement conditional catalog caching and explicit offline/stale behavior.
6. Implement streamed atomic/resumable PBF downloads and manifests.
7. Implement platform paths, dataset locks, staging, and atomic publication.
8. Implement injectable Docker discovery, inspection, execution, and error mapping.
9. Implement preflight planning for daemon, architecture, port, storage, and reuse.
10. Implement correct pinned MLD extract/partition/customize preparation.
11. Implement labeled start, loopback binding, readiness, status, logs, and stop.
12. Implement a Docker-independent typed OSRM route/table/nearest HTTP client.
13. Implement dry-run and targeted cleanup safeguards.
14. Add CLI adapters, JSON output, progress, cancellation, and exit codes.
15. Delegate legacy functions and add tested deprecation warnings.
16. Remove duplicate module and orchestration scripts after compatibility lands.
17. Add unit, contract, subprocess, concurrency, and failure-injection tests.
18. Add opt-in Docker integration and cross-platform manual acceptance workflow.
19. Verify installed sdist/wheel behavior and publish operations/troubleshooting docs.

Each sub-issue must define its exact public surface and test doubles. Do not combine
catalog resolution, Docker orchestration, and legacy removal in one PR.

## Verification matrix

### Hermetic PR tests

- fixture regions: `peru`, nested `sul`, slash-containing `us/new-york`, a region
  without ISO, multiple ISO aliases, missing PBF URL, invalid parent, duplicate ID,
  malformed catalog, ambiguity, and stale cache;
- exact subprocess argument and label assertions for Linux, macOS, and Windows path
  forms;
- `.osm.pbf` versus `.osrm` command sequencing;
- partial download resume/change, atomic failure, insufficient disk, occupied port,
  missing Docker, daemon denial, image failure, command failure, readiness timeout,
  Ctrl-C, concurrent prepare, and targeted cleanup;
- manifest-match reuse and mismatch-triggered rebuild;
- legacy signature/return/deprecation tests.

PR tests require neither Docker nor network access.

### Scheduled/manual integration

- resolve and download a deliberately small Geofabrik extract;
- prepare it with the pinned image;
- start OSRM, call route/table endpoints, validate units, and stop it;
- rerun to prove idempotent reuse;
- inject a second profile/port to prove isolation;
- clean only resources created by the job.

Automate Linux Docker integration. Record release-candidate manual evidence from
maintainers using Docker Desktop on macOS (including Apple Silicon where supported)
and Windows. A platform is not claimed as supported without evidence.

## Acceptance criteria

- `urls.pbf` from the official catalog is the only download URL source.
- Correct OSRM `.osm.pbf` to `.osrm` preparation is asserted in tests.
- macOS, Linux, and Windows use identical Python lifecycle logic.
- image, dataset, profile, and algorithm identity is reproducible in a manifest.
- concurrent and interrupted runs cannot publish corrupt prepared state.
- start succeeds only after bounded readiness verification.
- local services bind to loopback by default and the HTTP client works with both
  managed-local and explicitly configured remote endpoints.
- stop/clean operations can affect only exact UrbanPy-owned resources.
- legacy users receive a working adapter and documented migration path.
- installed wheel behavior, not merely repository execution, passes smoke tests.
- SonarQube, deterministic CI, security, and dependency compliance pass.

## Out of scope for 0.3

- hosting or operating a public OSRM service;
- silently fuzzy-matching region names;
- automatic planet-scale preparation;
- arbitrary custom Lua profiles;
- incremental Geofabrik replication updates;
- non-Docker container engines;
- packaging PBF or prepared graph data inside UrbanPy artifacts.

## Authoritative references

- Geofabrik technical catalog:
  <https://download.geofabrik.de/technical.html>
- Geofabrik no-geometry catalog:
  <https://download.geofabrik.de/index-v1-nogeom.json>
- OSRM backend and Docker quick start:
  <https://github.com/Project-OSRM/osrm-backend>
- OSRM HTTP API:
  <https://project-osrm.org/docs/v5.24.0/api/>
