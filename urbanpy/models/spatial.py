"""Small, immutable spatial and routing boundary values."""

from enum import StrEnum
from typing import Annotated, Self, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]


class _FrozenBoundaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Coordinate(_FrozenBoundaryModel):
    """A WGS84 longitude/latitude pair with unambiguous field names."""

    longitude: Longitude
    latitude: Latitude

    @classmethod
    def from_lon_lat(cls, values: Sequence[float]) -> Self:
        """Validate a two-item sequence in ``(longitude, latitude)`` order."""
        if len(values) != 2:
            raise ValueError("A coordinate requires exactly two values: (lon, lat).")
        return cls(longitude=values[0], latitude=values[1])

    def as_lon_lat(self) -> tuple[float, float]:
        """Return the coordinate in explicit ``(longitude, latitude)`` order."""
        return (self.longitude, self.latitude)


class BoundingBox(_FrozenBoundaryModel):
    """A non-antimeridian WGS84 box ordered west, south, east, north."""

    west: Longitude
    south: Latitude
    east: Longitude
    north: Latitude

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.west >= self.east:
            raise ValueError(
                "west must be less than east; antimeridian-crossing bounds "
                "are not supported"
            )
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        return self

    @classmethod
    def from_sequence(cls, values: Sequence[float]) -> Self:
        """Validate ``(west, south, east, north)`` values."""
        if len(values) != 4:
            raise ValueError(
                "A bounding box requires four values: (west, south, east, north)."
            )
        return cls(west=values[0], south=values[1], east=values[2], north=values[3])

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return ``(west, south, east, north)``."""
        return (self.west, self.south, self.east, self.north)


class TravelProfile(StrEnum):
    """Provider-neutral travel modes supported by UrbanPy routing APIs."""

    DRIVING = "driving"
    CYCLING = "cycling"
    WALKING = "walking"


__all__ = ["BoundingBox", "Coordinate", "TravelProfile"]
