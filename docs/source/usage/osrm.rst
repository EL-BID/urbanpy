Local OSRM service
==================

UrbanPy 0.3 manages a local `OSRM <https://project-osrm.org/>`__ service
through a cross-platform Python API. The former Bash and PowerShell scripts
have been removed. Trunk still checks any ordinary shell scripts in the
repository, but a linter cannot make lifecycle orchestration, partial
downloads, container ownership, or cleanup safe.

Requirements and constraints
----------------------------

Install Docker Desktop (macOS or Windows) or Docker Engine (Linux), start its
daemon, and allow enough disk space for both the Geofabrik PBF and prepared
OSRM files. Processing a country can take substantial time and disk space.

UrbanPy pins the official ``osrm/osrm-backend:v5.25.0`` image by digest for
reproducibility. The current official image is published for ``linux/amd64``;
Docker may therefore use emulation on Apple Silicon and other ARM systems.
Do not replace the digest with ``latest`` in production automation.

Prepare and start
-----------------

Use the canonical Geofabrik ``properties.id`` value. See :doc:`geofabrik` for
catalog discovery and the deliberately narrow ISO-code aliases.

.. code-block:: python

   from urbanpy.models import OSRMConfig, TravelProfile
   from urbanpy.routing import OSRMManager

   config = OSRMConfig(
       region_id="south-america/peru",
       profile=TravelProfile.WALKING,
   )
   manager = OSRMManager(config)

   plan = manager.plan()       # no Docker or filesystem mutation
   manager.prepare()           # download, extract, partition, customize
   status = manager.start()    # waits until the HTTP API is ready
   print(status.endpoint)

The MLD pipeline intentionally gives ``osrm-extract`` the
``data.osm.pbf`` input and gives ``osrm-partition``, ``osrm-customize``, and
``osrm-routed`` the resulting ``data.osrm`` base path. UrbanPy stages the
result and only publishes a complete dataset with a matching manifest.

Query independently of Docker
-----------------------------

``OSRMClient`` can call a service managed by UrbanPy or any compatible remote
OSRM endpoint. Coordinates are always longitude first, and returned durations
are seconds.

.. code-block:: python

   from urbanpy.models import Coordinate
   from urbanpy.routing import OSRMClient

   client = OSRMClient("http://127.0.0.1:5000")
   route = client.route(
       Coordinate(longitude=-77.0428, latitude=-12.0464),
       Coordinate(longitude=-77.0282, latitude=-12.1191),
   )
   print(route.distance_m, route.duration_s)

Operate and clean up
--------------------

.. code-block:: python

   manager.status()
   manager.logs(tail=100)
   manager.stop()

   # Destructive cleanup is a dry run unless explicitly confirmed.
   print(manager.clean(container=True, prepared=True, dry_run=True))
   manager.clean(container=True, prepared=True, dry_run=False)

The default bind address is loopback because the local OSRM server has no
authentication. A non-loopback address requires ``allow_external=True``.
UrbanPy only stops or removes containers carrying the exact ownership and
dataset labels it created; a colliding user-owned container is never adopted.

Migration from 0.2
------------------

``start_osrm_server`` and ``stop_osrm_server`` remain as warning-emitting
adapters for one release. They now validate the country against the official
catalog and raise typed exceptions instead of printing subprocess failures.
Move new code to ``OSRMConfig`` and ``OSRMManager``. The deleted
``unix_download.sh``, ``windows_download.ps1``, and notebook launcher are not
supported interfaces.
