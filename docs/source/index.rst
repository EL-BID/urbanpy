UrbanPy
*******

**Download, process, route, and visualize high-resolution urban geospatial
data.**

UrbanPy is an EL-BID open-source Python library for reproducible urban data and
accessibility workflows. It integrates common geospatial libraries and public
data providers behind focused helpers while preserving GeoDataFrame-native
outputs.

Version 0.3 is currently an alpha modernization. Evaluate prereleases against
your own data before production use and review the changelog for migrations.

Capabilities
------------

- Download boundaries, points of interest, street networks, and selected HDX
  population resources.
- Generate H3 grids, filter population points, overlay polygons, and aggregate
  urban indicators.
- Query routing providers or manage a reproducible local OSRM service.
- Compute accessibility surfaces and visualize geospatial results.
- Validate new provider and lifecycle boundaries with explicit typed models.

Quick example
-------------

.. code-block:: python

   import urbanpy as up

   boundary = up.download.nominatim_osm(
       "Lima, Peru",
       expected_position=0,
       email="your-project-contact@example.org",
   )
   hexagons = up.geom.gen_hexagons(resolution=9, city=boundary)
   hexagons.plot()

Nominatim requires an identifying contact address. Provider-backed functions
remain subject to provider usage policies and data licenses.

Project links
-------------

- `Source and issues <https://github.com/EL-BID/urbanpy>`__
- `Changelog <https://github.com/EL-BID/urbanpy/blob/master/CHANGELOG.md>`__
- `Support policy <https://github.com/EL-BID/urbanpy/blob/master/SUPPORT.md>`__
- `Private security reporting <https://github.com/EL-BID/urbanpy/security/advisories/new>`__
- `Governance <https://github.com/EL-BID/urbanpy/blob/master/GOVERNANCE.md>`__

.. toctree::
   :caption: User guide
   :maxdepth: 2

   usage/installation
   usage/quickstart
   usage/geofabrik
   usage/osrm
   usage/api-stability
   usage/support

.. toctree::
   :caption: API and project
   :maxdepth: 3

   urbanpy
   contributing
   code_of_conduct
   license

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
