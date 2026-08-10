import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from urbanpy.errors import BoundaryValidationError
from urbanpy.models import BoundingBox, Coordinate, TravelProfile


@given(
    longitude=st.floats(min_value=-180, max_value=180, allow_nan=False),
    latitude=st.floats(min_value=-90, max_value=90, allow_nan=False),
)
def test_coordinate_round_trips_valid_wgs84_values(longitude, latitude):
    coordinate = Coordinate(longitude=longitude, latitude=latitude)

    assert coordinate.as_lon_lat() == (longitude, latitude)
    assert Coordinate.from_lon_lat(coordinate.as_lon_lat()) == coordinate


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [(-180.1, 0), (180.1, 0), (0, -90.1), (0, 90.1), (math.inf, 0), (0, math.nan)],
)
def test_coordinate_rejects_out_of_range_or_non_finite_values(longitude, latitude):
    with pytest.raises(ValidationError):
        Coordinate(longitude=longitude, latitude=latitude)


def test_boundary_models_are_strict_frozen_and_forbid_extra_fields():
    coordinate = Coordinate(longitude=-77.04, latitude=-12.06)

    with pytest.raises(ValidationError):
        Coordinate.model_validate({"longitude": "-77.04", "latitude": -12.06})
    with pytest.raises(ValidationError):
        Coordinate(longitude=-77.04, latitude=-12.06, altitude=10)
    with pytest.raises(ValidationError):
        coordinate.latitude = 0


@given(
    west=st.floats(min_value=-180, max_value=179, allow_nan=False),
    width=st.floats(min_value=0.000001, max_value=1, allow_nan=False),
    south=st.floats(min_value=-90, max_value=89, allow_nan=False),
    height=st.floats(min_value=0.000001, max_value=1, allow_nan=False),
)
def test_bounding_box_round_trips_ordered_values(west, width, south, height):
    east = min(west + width, 180)
    north = min(south + height, 90)
    box = BoundingBox(west=west, south=south, east=east, north=north)

    assert BoundingBox.from_sequence(box.as_tuple()) == box


@pytest.mark.parametrize(
    "values",
    [(-77, -12, -77, -11), (-76, -12, -77, -11), (-77, -11, -76, -11)],
)
def test_bounding_box_rejects_empty_reversed_or_antimeridian_bounds(values):
    with pytest.raises(ValidationError):
        BoundingBox.from_sequence(values)


def test_travel_profiles_have_stable_provider_neutral_values():
    assert [profile.value for profile in TravelProfile] == [
        "driving",
        "cycling",
        "walking",
    ]


def test_safe_boundary_error_does_not_echo_rejected_input():
    secret_like_value = "token-that-must-not-appear"
    with pytest.raises(ValidationError) as captured:
        Coordinate.model_validate(
            {"longitude": secret_like_value, "latitude": -12.06}
        )

    error = BoundaryValidationError.from_pydantic("coordinate", captured.value)

    assert str(error) == "Invalid coordinate at longitude."
    assert error.issues[0].field_path == "longitude"
    assert secret_like_value not in str(error)
    assert secret_like_value not in repr(error.issues)


def test_public_model_schemas_describe_units_ranges_and_required_fields():
    coordinate_schema = Coordinate.model_json_schema()
    bounds_schema = BoundingBox.model_json_schema()

    assert coordinate_schema["required"] == ["longitude", "latitude"]
    assert coordinate_schema["properties"]["longitude"]["minimum"] == -180
    assert coordinate_schema["properties"]["latitude"]["maximum"] == 90
    assert bounds_schema["required"] == ["west", "south", "east", "north"]
