# Pydantic and safe data-type plan for UrbanPy 0.3

## Outcome

Use Pydantic v2 and static annotations to make configuration, external service
payloads, and intentionally stable public results explicit and safe while
preserving native geospatial objects for computation.

Pydantic is currently present only as one of many pinned packages in
`requirements.txt`; UrbanPy does not use it. If UrbanPy imports Pydantic directly,
it becomes a declared direct dependency with a tested version range.

## Boundary-first policy

Use Pydantic at boundaries where untrusted or serialized data enters or leaves:

- public configuration and CLI input;
- HTTP request parameters and the external JSON fields UrbanPy consumes;
- durable cache records and OSRM preparation manifests;
- stable public result/configuration objects;
- parsing legacy dictionaries, tuples, and environment values.

Keep these native in computational paths:

- `GeoDataFrame` and `GeoSeries`;
- pandas and NumPy arrays/scalars;
- Shapely geometries;
- NetworkX/OSMnx graphs;
- rasters and other large domain arrays.

Do not create one model per GeoDataFrame row or validate large arrays element by
element by default. Validate the container contract once—geometry type, CRS,
required columns, shape, coordinate conventions—and let the native library own
the bulk data.

Static typing and runtime validation are complementary. All supported public
Python APIs receive precise annotations; only boundary data receives runtime
validation.

## Model taxonomy and stability

### Public domain models

Place intentionally supported contracts under `urbanpy.models` or documented
feature namespaces. Examples:

- `Coordinate`: named `longitude` and `latitude`, finite and range-checked;
- `BoundingBox`: `west`, `south`, `east`, `north`, with ordering and antimeridian
  behavior explicit;
- `TravelProfile`: constrained values and service-specific mappings;
- `GeofabrikRegion`: canonical region identity, parent, ISO aliases, and public
  PBF URL;
- `OSRMConfig`: region, profile, image, port, paths, timeouts, and policy;
- `OSRMStatus`: lifecycle state, endpoint, dataset/image identity, and diagnostics;
- `RouteResult`: explicit `distance_m` and `duration_s`, with optional geometry
  only if a stable serialization is specified;
- matrix metadata describing row/column identity and units without wrapping the
  underlying NumPy array.

These models follow the normal compatibility/deprecation policy. Model field names,
defaults, JSON serialization, and generated schema are public API.

### Internal transport models

Third-party payload schemas live in internal client modules, for example
`urbanpy._clients.geofabrik`. They model only consumed fields, tolerate documented
additional upstream fields, and translate into UrbanPy domain models. They are not
re-exported and can evolve with upstream APIs without creating public API debt.

### Lightweight typed structures

Use `TypedDict`, `Protocol`, `TypeAlias`, `NamedTuple`, or a standard dataclass when
runtime validation/serialization is not needed. `TypeAdapter` can validate a
collection or `TypedDict` without inventing a public `BaseModel`.

Do not make exceptions into Pydantic models. Define a small, stable UrbanPy
exception hierarchy that wraps transport and validation failures while preserving
safe structured context.

## Validation conventions

- Use Pydantic v2 APIs and `ConfigDict`; do not add v1 compatibility code.
- Use strict validation when coercion could conceal coordinate, unit, profile,
  identifier, boolean, or port mistakes. Permit intentional convenience coercion
  only in a named legacy/input adapter with tests.
- UrbanPy-owned configuration uses `extra="forbid"`. Third-party transport models
  normally ignore unknown fields but require all fields UrbanPy actually uses.
- Prefer immutable/frozen value models where mutation would invalidate a manifest
  or cache identity.
- Do not enable `arbitrary_types_allowed=True` globally. A native object accepted
  without validation should stay outside the model or have a focused adapter.
- Reject non-finite coordinates and numeric values. State whether Z coordinates
  are ignored, rejected, or preserved.
- Encode units in field names (`distance_m`, `duration_s`) and docs, not only prose.
- Coordinate tuple adapters must state and test order. Public models use named
  fields to avoid `(lat, lon)` versus `(lon, lat)` ambiguity.
- CRS-bearing inputs use shared validation helpers and `pyproj.CRS` normalization;
  a missing CRS is never silently assumed for an operation where it affects
  correctness.
- Secrets use redacted representations and never appear in validation errors,
  model dumps, logs, or `repr`.
- Validation errors report a stable error category, field path, expected form,
  and remediation without echoing entire external payloads.
- JSON serialization is deterministic where used for manifests/cache keys.

## API migration rules

- Normalize a legacy input once at the boundary; internal code receives the new
  model or native normalized type.
- New APIs may accept a model plus documented plain-Python conveniences.
- Avoid decorating every public function with `validate_call`; it changes error
  semantics and adds overhead. Use explicit boundary adapters where behavior is
  controllable and benchmarked.
- When replacing a tuple/dict result would break unpacking or equality, introduce
  a parallel typed API first. Keep the legacy result adapter for the documented
  deprecation window.
- Public deprecations use a visible warning category, correct `stacklevel`, docs,
  tests, changelog entry, and a scheduled removal version.
- Pydantic `ValidationError` may be preserved as the cause, but the public API
  raises a documented UrbanPy boundary/configuration exception where consistency
  matters.
- Do not silently change coordinate order, CRS, distance unit, duration unit, or
  null/sentinel behavior during model adoption.

## Static typing plan

- Select one stable CI type checker in an ADR. Mypy is the initial recommendation
  because Pydantic maintains a v2 plugin; verify behavior with current geospatial
  stubs before committing.
- Add `py.typed` only when annotations shipped to users are checked and supported.
- Start strictness with new model/client/OSRM modules, then migrate one existing
  module at a time. Do not hide the entire current package behind blanket ignores.
- Add and pin needed stub packages in the type-check dependency group, not runtime.
- Use protocols at subprocess/HTTP boundaries to make fakes type-safe and avoid
  coupling tests to concrete clients.
- Type-check code examples that claim to be supported.

## Initial shared model slice

The Pydantic epic should not block all OSRM work. Its first independently
deliverable slice is:

1. `Coordinate` and `BoundingBox` plus native geometry/container validators;
2. `TravelProfile` and explicit OSRM API profile mapping;
3. `GeofabrikRegion` plus internal v1 catalog transport models;
4. `OSRMConfig`, manifest identity, and `OSRMStatus`;
5. base exceptions and safe validation-error translation.

Freeze this slice only after the catalog and Docker manager consumers have been
implemented together in tests. Avoid designing unused generic models.

## Module migration order

1. **Geofabrik/OSRM:** best-defined new boundary and immediate production need.
2. **Shared HTTP configuration/errors:** timeouts, endpoints, identification,
   retry/caching policy, and safe response metadata.
3. **Routing APIs:** coordinates, profiles, distance/duration results, matrix
   dimensions/units, and provider responses.
4. **Download clients:** Nominatim, Overpass, and HDX request/response boundaries.
5. **Geometry/accessibility:** validate CRS, geometry kind, columns, resolution,
   and numeric parameters without wrapping whole frames.
6. **Plotting:** validate small option/config inputs only if current errors justify
   runtime models.

Every module migration includes behavior characterization first. Existing defects
are not frozen as compatibility unless explicitly documented.

## GitHub sub-issues

1. Inventory public inputs/outputs, current sentinels, coordinate order, CRS, and
   units across all exported functions.
2. Write ADR for runtime versus static typing and model stability boundaries.
3. Select Pydantic/Python/type-checker ranges and measure dependency impact.
4. Define exception, units, CRS, naming, serialization, and deprecation conventions.
5. Implement/test coordinate, bounds, profile, and safe URL primitives.
6. Implement internal Geofabrik v1 transport and public region model.
7. Implement OSRM configuration, manifest identity, status, and result models.
8. Add schema snapshots and generated schema documentation for public models.
9. Add public package typing baseline and type-safe HTTP/subprocess protocols.
10. Migrate routing boundaries while preserving legacy tuple/array adapters.
11. Migrate Nominatim/Overpass/HDX boundaries and typed service errors.
12. Add GeoDataFrame/GeoSeries precondition helpers for CRS, columns, and geometry.
13. Migrate geometry/accessibility boundaries module by module.
14. Benchmark validation/import/serialization cost on representative workloads.
15. Publish model/API migration guidance and deprecation schedule.

Each implementation issue must name a real boundary and consumer. “Add models for
module X” is not sufficiently defined.

## Verification

- Unit tests cover valid, invalid, boundary, strict/coercion, redaction,
  serialization, and round-trip behavior.
- Property-based tests cover finite coordinate ranges, bounding-box ordering,
  region identifiers, ports, timeouts, and matrix dimensions.
- Fixture contract tests cover extra/missing/null/wrong-type third-party fields
  without live network calls.
- Schema snapshots detect accidental field/default/serialization changes.
- Compatibility tests cover old signatures, tuple/array ordering, warnings, and
  exception translation.
- Static type tests cover production modules and supported examples, including
  negative/error examples where the checker supports them.
- Benchmarks compare import time, single-object validation, catalog parsing, and
  representative large GeoDataFrame operations. Large frames receive no per-row
  Pydantic pass by default.
- Built-wheel tests confirm `py.typed`, public imports, and generated schemas are
  actually packaged.
- SonarQube continues to analyze migrated code and remains required.

## Acceptance criteria

- Every public model has a documented boundary, owner, consumer, stability level,
  example, and schema test.
- Every internal transport model translates into a domain/native type and is not
  accidentally re-exported.
- The OSRM/Geofabrik path has no unchecked dictionary traversal.
- Coordinates, CRS, distance units, duration units, and null behavior are explicit.
- Large geospatial objects incur no per-row Pydantic validation by default.
- Secrets and full external payloads cannot leak through validation errors/logs.
- Existing callers have a tested adapter and migration path for changed behavior.
- Static annotations, runtime behavior, documentation, and packaged schemas agree.
- Validation overhead stays within an agreed budget and is negligible relative to
  network/geospatial work at the chosen boundaries.

## Out of scope for 0.3

- replacing GeoPandas, pandas, Shapely, NumPy, or NetworkX domain objects;
- validating every dataframe row or array element;
- exposing raw third-party response models as permanent UrbanPy API;
- using Pydantic models merely to increase model count or typing coverage;
- environment-driven global settings without a demonstrated use case;
- changing all existing return values in one breaking migration.

## Authoritative references

- Pydantic models and configuration: <https://docs.pydantic.dev/latest/>
- Pydantic strict mode:
  <https://docs.pydantic.dev/latest/concepts/strict_mode/>
- Pydantic performance guidance:
  <https://docs.pydantic.dev/latest/concepts/performance/>
- Pydantic mypy plugin:
  <https://docs.pydantic.dev/latest/integrations/mypy/>
- PEP 561 typed packages: <https://peps.python.org/pep-0561/>

