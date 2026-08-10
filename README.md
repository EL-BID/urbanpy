[![CI](https://github.com/EL-BID/urbanpy/actions/workflows/main.yml/badge.svg)](https://github.com/EL-BID/urbanpy/actions/workflows/main.yml)
[![SonarQube](https://github.com/EL-BID/urbanpy/actions/workflows/build.yml/badge.svg)](https://github.com/EL-BID/urbanpy/actions/workflows/build.yml)
[![Downloads](https://static.pepy.tech/badge/urbanpy)](https://pepy.tech/project/urbanpy)
[![Downloads](https://static.pepy.tech/badge/urbanpy/month)](https://pepy.tech/project/urbanpy)
[![Downloads](https://static.pepy.tech/badge/urbanpy/week)](https://pepy.tech/project/urbanpy)
# UrbanPy 🏙️

**Download, process, route, and visualize high-resolution urban geospatial data.**

UrbanPy is an EL-BID open-source Python library for reproducible urban data and
accessibility workflows. Version 0.3 is currently an alpha modernization: use a
stable 0.2 release for established production deployments and test 0.3 against
your data before upgrading.

# Functional goals

- [x] Download open source spatial data (Limits & Points of Interests)
- [x] Allow for the use of a grid system or administrative boundaries as spatial units.
- [x] Origin-destination matrix calculation by any mode using a routing API
- [x] Obtain travel time from spatial units to the closest facilities
- [x] Consolidate the results as tables and/or shapefiles (georeferenced datasets)
- [x] Visualise the results as maps

# UX goals

- [ ] Atomic functions (one purpose per function)
- [x] Use the power of Python Geospatial Ecosystem under the hood
- [x] Allow to flexible processing pipelines (custom layer/metrics aggregations)
- [x] Clear documentation with usage and examples
- [x] Clear and replicable example notebooks

## Main modules

- download: Main functions for data download from Nominatin API, OverPass API and HDX population data
- geom: Spatial operations, grid partitioning, spatial filtering and street network statistics
- plotting: Visualization wrappers for plotly interactive choropleth maps
- routing: Distance matrix computations (may require your own API keys)
- utils: Data handling helpers

## Installation

### For users

Install the stable release from PyPI:

```sh
python -m pip install urbanpy
```

Then use `import urbanpy` in your python scripts to use the library.

The normal routing, geometry, and provider clients do not require a local OSRM
container. To prepare and operate a local OSRM service, install Docker and follow
the [OSRM guide](https://el-bid.github.io/urbanpy/usage/osrm.html). UrbanPy 0.3
uses a cross-platform Python lifecycle; it never requires weakening PowerShell's
execution policy.

### Geospatial dependencies

Current GeoPandas, Shapely, OSMnx, and H3 releases provide wheels for common
platforms. If installation must compile a dependency, install that project's
documented system toolchain. Large OSRM regions require substantial disk, memory,
and processing time; begin with a small canonical Geofabrik region.

# Examples

UrbanPy lets you download and visualize city boundaries extremely easy:

```python
import urbanpy as up

boundaries = up.download.nominatim_osm('Lima, Peru', expected_position=2, email="your@email.com")
boundaries.plot()
```

Since `boundaries` is a GeoDataFrame it can be easily plotted with the method `.plot()`. You can also generate hexagons to fill the city boundaries in a oneliner.

```python
hexes = up.geom.gen_hexagons(resolution=9, city=boundaries)
```

See the [documentation](https://el-bid.github.io/urbanpy/) and
[example notebooks](https://nbviewer.org/github/EL-BID/urbanpy/tree/master/notebooks/).

### For developers

Install [uv](https://docs.astral.sh/uv/), clone the repository, and create the
locked development environment:

```sh
uv sync --locked --all-groups
uv run pytest
trunk check
```

## License

UrbanPy is licensed under [GPL-3.0-only](LICENSE). Data downloaded through
UrbanPy remains subject to each provider's terms and license.

## Authors

UrbanPy's original authors are Claudio Ortega ([socials](https://www.linkedin.com/in/claudioortega27/)), Andrés Regal ([socials](https://www.linkedin.com/in/andrés-regal/)), and Antonio Vazquez Brust ([socials](https://www.linkedin.com/in/avazquez/)).

## Contribution guidelines

**If you want to contribute to UrbanPy, be sure to review the
[contribution guidelines](CONTRIBUTING.md). This project adheres to UrbanPy's
[code of conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code.**

See [SUPPORT.md](SUPPORT.md), [GOVERNANCE.md](GOVERNANCE.md), and
[SECURITY.md](SECURITY.md) for maintenance, decision-making, and private
vulnerability reporting. Supported Python versions are tested in CI; OSRM
platform claims require separate Docker release evidence.

## Citation

If you use this library or find the documentation useful for your research, please consider citing:

```
@InProceedings{urbanpy,
    author="Regal, Andres and Ortega, Claudio and Vazquez Brust, Antonio and Rodriguez, Michelle and Zambrano-Barragan, Patricio",
    title="UrbanPy: A Library to Download, Process and Visualize High Resolution Urban Data to Support Transportation and Urban Planning Decisions",
    booktitle="Production and Operations Management",
    year="2022",
    publisher="Springer International Publishing",
    address="Cham",
    pages="463--473",
    isbn="978-3-031-06862-1",
    url="https://doi.org/10.1007/978-3-031-06862-1_34"
}
```

## Contributors

<a href="https://github.com/EL-BID/urbanpy/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=EL-BID/urbanpy" />
</a>

## Use Cases

[Urbanpy applied to the education sector in Brasil](https://github.com/EL-BID/IADB-education-1)
This repo is for code, documentation, and discussion for work associated with a skills-based volunteering project in collaboration with the IADB and urbanpy.

## Related projects

<a href="https://www.autodash.org/">
  <img src="https://www.autodash.org/static/images/logo.png" width=64 height=64 /><p>AutoDash</p>
</a>
