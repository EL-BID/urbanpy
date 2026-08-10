Installation
============

Users
-----

Install the stable release from PyPI in a virtual environment:

.. code-block:: console

   python -m pip install urbanpy

Then verify the import and version:

.. code-block:: pycon

   >>> import urbanpy
   >>> urbanpy.__version__

UrbanPy supports the Python versions declared in ``pyproject.toml`` and tested
in CI. Current geospatial dependencies publish wheels for common platforms. If
your platform must compile a dependency, follow that dependency's system
toolchain documentation.

Local OSRM is optional. Install and start Docker, then follow :doc:`osrm`.
Normal geometry operations and calls to independently operated routing services
do not require Docker.

Prereleases
-----------

Version 0.3 alpha, beta, and release-candidate builds are evaluation releases.
Install a specific prerelease only when intentionally testing its migration:

.. code-block:: console

   python -m pip install --pre "urbanpy==0.3.0a0"

Do not assume cache, model, or deprecated API stability between alpha builds.
Review the project changelog and test representative geospatial data first.

Developers
----------

Install `uv <https://docs.astral.sh/uv/>`__, clone the repository, then run:

.. code-block:: console

   uv sync --locked --all-groups
   uv run pytest
   trunk check

The committed ``uv.lock`` is authoritative for development and CI. Runtime
users receive the compatible dependency ranges declared in ``pyproject.toml``.
See :doc:`../contributing` for test markers and pull-request requirements.
