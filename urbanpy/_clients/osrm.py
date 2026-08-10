"""Internal schemas for the small subset of OSRM responses UrbanPy consumes."""

from pydantic import BaseModel, ConfigDict, Field

from urbanpy.models import RouteResult, TableResult


class _TransportModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class _Route(_TransportModel):
    distance: float = Field(ge=0, allow_inf_nan=False)
    duration: float = Field(ge=0, allow_inf_nan=False)


class RouteResponse(_TransportModel):
    code: str
    routes: list[_Route]

    def to_result(self) -> RouteResult:
        if self.code != "Ok" or not self.routes:
            raise ValueError(f"OSRM route failed with code {self.code!r}")
        route = self.routes[0]
        return RouteResult(distance_m=route.distance, duration_s=route.duration)


class TableResponse(_TransportModel):
    code: str
    distances: list[list[float | None]]
    durations: list[list[float | None]]

    def to_result(self) -> TableResult:
        if self.code != "Ok":
            raise ValueError(f"OSRM table failed with code {self.code!r}")
        return TableResult(
            distances_m=tuple(tuple(row) for row in self.distances),
            durations_s=tuple(tuple(row) for row in self.durations),
        )


class NearestResponse(_TransportModel):
    code: str


__all__ = ["NearestResponse", "RouteResponse", "TableResponse"]
