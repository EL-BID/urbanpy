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

## Capabilities

- Download open spatial boundaries, points of interest, street networks, and
  selected population datasets.
- Generate H3 grids and combine native GeoPandas, Shapely, OSMnx, and NetworkX
  objects in custom analysis pipelines.
- Calculate origin-destination matrices, routes, isochrones, nearest-facility
  travel times, and accessibility indicators.
- Operate an optional reproducible local OSRM service from canonical Geofabrik
  extracts without platform-specific shell scripts.
- Produce GeoDataFrame outputs and interactive Plotly maps.

## Main modules

- `download`: Nominatim, Overpass, OSMnx, and selected HDX provider helpers.
- `geom`: spatial operations, H3 grids, filtering, overlays, and network statistics.
- `plotting`: interactive Plotly choropleth maps.
- `routing`: provider routing, isochrones, matrices, and local OSRM lifecycle.
- `accessibility`: nearest-facility and accessibility indicators.
- `models`: stable validated coordinate, region, routing, and lifecycle values.
- `utils`: lower-level geospatial data helpers.

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

Download and visualize a city boundary while identifying your application to
the public Nominatim service:

```python
import urbanpy as up

boundaries = up.download.nominatim_osm(
    "Lima, Peru",
    expected_position=2,
    email="your-project-contact@example.org",
)
boundaries.plot()
```

Because `boundaries` is a GeoDataFrame, it works directly with the normal
GeoPandas API. Generate an H3 grid over the selected geometry:

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
