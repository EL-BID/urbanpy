Canonical Geofabrik regions
===========================

Geofabrik publishes its programmatic extract catalog at
``https://download.geofabrik.de/index-v1-nogeom.json``. UrbanPy treats each
feature's ``properties.id`` as the canonical identifier and consumes
``properties.urls.pbf`` verbatim. It does not assemble a URL from guessed
continent and country names.

Load the catalog and resolve either an exact canonical ID or an advertised ISO
3166 code:

.. code-block:: python

   from urbanpy.geofabrik import GeofabrikCatalog

   catalog = GeofabrikCatalog.fetch()
   peru = catalog.resolve("peru")       # canonical properties.id
   same = catalog.resolve("PE")         # advertised ISO 3166-1 alias
   california = catalog.resolve("US-CA")

   assert california.id == "us/california"
   print(california.pbf_url)

Nested IDs matter. ``california`` is not silently expanded to
``us/california``; use the full ID or ``US-CA``. Display names, filename stems,
and partial paths are not stable programmatic aliases. Unknown and ambiguous
identifiers raise explicit lookup errors.

The catalog request identifies UrbanPy, uses connect/read timeouts, requires an
official HTTPS PBF URL, limits response size, and translates malformed provider
payloads without logging their full contents.
