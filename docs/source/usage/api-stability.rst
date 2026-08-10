Public API and compatibility
============================

UrbanPy's supported public surface consists of names documented in this guide
and names listed in a public module's ``__all__``. Private modules and names
beginning with an underscore are implementation details. Third-party objects
that happen to be imported by a module are not UrbanPy APIs.

Stability levels
----------------

- The ``0.3`` alpha series may make documented compatibility corrections before
  the stable release.
- A stable ``0.x`` public name is changed only with a changelog entry and a
  migration path when practical.
- Deprecations emit ``FutureWarning`` with a caller-oriented stack location and
  normally remain available for at least one minor release.
- Pydantic models exported from ``urbanpy.models`` are public contracts. Their
  field names, units, validation, and serialized form follow the same policy.
- ``GeoDataFrame``, Shapely, NetworkX, NumPy, and pandas values remain native;
  UrbanPy does not wrap every row in a validation model.

Boundary conventions
--------------------

``Coordinate`` uses explicit longitude and latitude fields. ``BoundingBox`` and
legacy four-value bounds use ``(west, south, east, north)`` in WGS84 and reject
antimeridian-crossing boxes. Routing result units are encoded in field names,
including ``distance_m`` and ``duration_s``. Invalid typed boundaries raise
``urbanpy.BoundaryValidationError`` without including rejected provider payloads.

The provider-backed download helpers retain GeoDataFrame-native results. Their
availability, rate limits, and mutable data are upstream service contracts, not
library stability guarantees.
