"""Docker-independent typed client for an OSRM HTTP endpoint."""

from collections.abc import Sequence
from typing import Any, Final

import requests
from pydantic import ValidationError

from urbanpy._clients.osrm import NearestResponse, RouteResponse, TableResponse
from urbanpy.errors import BoundaryValidationError, UrbanPyError
from urbanpy.models import Coordinate, RouteResult, TableResult, TravelProfile

MAX_RESPONSE_BYTES: Final = 20 * 1024 * 1024
API_PROFILES: Final = {
    TravelProfile.DRIVING: "driving",
    TravelProfile.CYCLING: "cycling",
    TravelProfile.WALKING: "walking",
}


class OSRMClientError(UrbanPyError):
    """An OSRM endpoint or response failed."""


class OSRMClient:
    """Call a managed local or independently operated OSRM endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (3.0, 30.0),
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

    def route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        *,
        profile: TravelProfile = TravelProfile.DRIVING,
    ) -> RouteResult:
        coordinates = f"{_coordinate(origin)};{_coordinate(destination)}"
        payload = self._get(
            f"/route/v1/{API_PROFILES[profile]}/{coordinates}",
            params={"overview": "false"},
        )
        try:
            return RouteResponse.model_validate(payload).to_result()
        except ValidationError as error:
            raise BoundaryValidationError.from_pydantic(
                "OSRM route response", error
            ) from error
        except ValueError as error:
            raise OSRMClientError(str(error)) from error

    def table(
        self,
        origins: Sequence[Coordinate],
        destinations: Sequence[Coordinate],
        *,
        profile: TravelProfile = TravelProfile.DRIVING,
    ) -> TableResult:
        if not origins or not destinations:
            raise ValueError("OSRM table requires at least one origin and destination.")
        all_coordinates = [*origins, *destinations]
        coordinates = ";".join(_coordinate(value) for value in all_coordinates)
        source_indices = ";".join(str(index) for index in range(len(origins)))
        destination_indices = ";".join(
            str(index) for index in range(len(origins), len(all_coordinates))
        )
        payload = self._get(
            f"/table/v1/{API_PROFILES[profile]}/{coordinates}",
            params={
                "annotations": "distance,duration",
                "destinations": destination_indices,
                "sources": source_indices,
            },
        )
        try:
            return TableResponse.model_validate(payload).to_result()
        except ValidationError as error:
            raise BoundaryValidationError.from_pydantic(
                "OSRM table response", error
            ) from error
        except ValueError as error:
            raise OSRMClientError(str(error)) from error

    def ready(self, *, profile: TravelProfile = TravelProfile.DRIVING) -> bool:
        try:
            payload = self._get(
                f"/nearest/v1/{API_PROFILES[profile]}/0,0", params={"number": "1"}
            )
            response = NearestResponse.model_validate(payload)
        except (OSRMClientError, BoundaryValidationError, ValidationError):
            return False
        return response.code in {"Ok", "NoSegment"}

    def _get(self, path: str, *, params: dict[str, str]) -> Any:
        try:
            response = self.session.get(
                f"{self.base_url}{path}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise OSRMClientError("OSRM request failed.") from error
        if len(response.content) > self.max_response_bytes:
            raise OSRMClientError("OSRM response exceeds the configured size limit.")
        try:
            return response.json()
        except requests.JSONDecodeError as error:
            raise OSRMClientError("OSRM response is not valid JSON.") from error


def _coordinate(value: Coordinate) -> str:
    return f"{value.longitude:.8f},{value.latitude:.8f}"


__all__ = ["OSRMClient", "OSRMClientError"]
