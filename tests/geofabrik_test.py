from unittest.mock import Mock

import pytest

from urbanpy.errors import BoundaryValidationError
from urbanpy.geofabrik import (
    DEFAULT_TIMEOUT,
    GEOFABRIK_INDEX_URL,
    MAX_CATALOG_BYTES,
    USER_AGENT,
    GeofabrikCatalog,
    GeofabrikCatalogError,
    GeofabrikRegionAmbiguous,
    GeofabrikRegionNotFound,
)


def _feature(
    region_id,
    parent,
    url,
    *,
    name=None,
    iso_alpha2=None,
    iso_3166_2=None,
):
    properties = {
        "id": region_id,
        "name": name or region_id,
        "parent": parent,
        "urls": {"pbf": url, "upstream-field": "ignored"},
        "upstream-field": "ignored",
    }
    if iso_alpha2 is not None:
        properties["iso3166-1:alpha2"] = iso_alpha2
    if iso_3166_2 is not None:
        properties["iso3166-2"] = iso_3166_2
    return {"type": "Feature", "properties": properties}


@pytest.fixture
def catalog_payload():
    return {
        "type": "FeatureCollection",
        "features": [
            _feature(
                "peru",
                "south-america",
                "https://download.geofabrik.de/south-america/peru-latest.osm.pbf",
                name="Peru",
                iso_alpha2=["PE"],
            ),
            _feature(
                "us/california",
                "north-america",
                "https://download.geofabrik.de/north-america/us/california-latest.osm.pbf",
                iso_3166_2=["US-CA"],
            ),
            _feature(
                "georgia",
                "europe",
                "https://download.geofabrik.de/europe/georgia-latest.osm.pbf",
                name="Georgia",
                iso_alpha2=["GE"],
            ),
        ],
        "future-top-level-field": True,
    }


def test_resolves_exact_canonical_ids_and_iso_aliases(catalog_payload):
    catalog = GeofabrikCatalog.from_payload(catalog_payload)

    assert catalog.resolve("peru").id == "peru"
    assert catalog.resolve("PERU").id == "peru"
    assert catalog.resolve("PE").id == "peru"
    assert catalog.resolve("US-CA").id == "us/california"
    assert catalog.resolve("ge").parent == "europe"


def test_uses_catalog_pbf_url_verbatim_including_nested_ids(catalog_payload):
    catalog = GeofabrikCatalog.from_payload(catalog_payload)

    california = catalog.resolve("us/california")

    assert str(california.pbf_url) == (
        "https://download.geofabrik.de/north-america/us/california-latest.osm.pbf"
    )


def test_does_not_guess_display_names_or_partial_path_segments(catalog_payload):
    catalog = GeofabrikCatalog.from_payload(catalog_payload)

    with pytest.raises(GeofabrikRegionNotFound, match="properties.id"):
        catalog.resolve("california")
    with pytest.raises(GeofabrikRegionNotFound, match="Region is empty"):
        catalog.resolve("  ")


def test_rejects_ambiguous_iso_aliases(catalog_payload):
    duplicate = _feature(
        "test-region",
        "europe",
        "https://download.geofabrik.de/europe/test-region-latest.osm.pbf",
        iso_alpha2=["PE"],
    )
    catalog_payload["features"].append(duplicate)
    catalog = GeofabrikCatalog.from_payload(catalog_payload)

    with pytest.raises(GeofabrikRegionAmbiguous, match="peru, test-region"):
        catalog.resolve("PE")


def test_rejects_duplicate_canonical_ids(catalog_payload):
    catalog_payload["features"].append(catalog_payload["features"][0])

    with pytest.raises(GeofabrikCatalogError, match="Duplicate canonical"):
        GeofabrikCatalog.from_payload(catalog_payload)


@pytest.mark.parametrize(
    "url",
    [
        "http://download.geofabrik.de/europe/test-latest.osm.pbf",
        "https://example.org/europe/test-latest.osm.pbf",
        "https://download.geofabrik.de/europe/test.osm.pbf",
    ],
)
def test_rejects_noncanonical_or_unsafe_pbf_urls(catalog_payload, url):
    catalog_payload["features"][0]["properties"]["urls"]["pbf"] = url

    with pytest.raises(BoundaryValidationError):
        GeofabrikCatalog.from_payload(catalog_payload)


def test_fetch_identifies_client_sets_timeouts_and_enforces_size(catalog_payload):
    response = Mock()
    response.content = b"{}"
    response.json.return_value = catalog_payload
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response

    catalog = GeofabrikCatalog.fetch(session=session)

    assert catalog.resolve("PE").id == "peru"
    session.get.assert_called_once_with(
        GEOFABRIK_INDEX_URL,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
    )

    response.content = b"x" * (MAX_CATALOG_BYTES + 1)
    with pytest.raises(GeofabrikCatalogError, match="safety limit"):
        GeofabrikCatalog.fetch(session=session)


def test_fetch_translates_transport_and_json_errors(catalog_payload):
    session = Mock()
    session.get.side_effect = __import__("requests").Timeout("timed out")
    with pytest.raises(GeofabrikCatalogError, match="Could not fetch"):
        GeofabrikCatalog.fetch(session=session)

    response = Mock()
    response.content = b"not-json"
    response.raise_for_status.return_value = None
    response.json.side_effect = __import__("requests").JSONDecodeError(
        "bad", "not-json", 0
    )
    session.get.side_effect = None
    session.get.return_value = response
    with pytest.raises(GeofabrikCatalogError, match="not valid JSON"):
        GeofabrikCatalog.fetch(session=session)


def test_missing_consumed_catalog_fields_are_safe_validation_errors():
    payload = {"type": "FeatureCollection", "features": [{"properties": {}}]}

    with pytest.raises(BoundaryValidationError) as captured:
        GeofabrikCatalog.from_payload(payload)

    assert "properties" in str(captured.value)
    assert repr(payload) not in str(captured.value)
