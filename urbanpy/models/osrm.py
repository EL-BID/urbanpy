"""Public configuration and result contracts for OSRM."""

from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    IPvAnyAddress,
    StrictInt,
    model_validator,
)

from .geofabrik import RegionId
from .spatial import TravelProfile

DEFAULT_OSRM_IMAGE = (
    "osrm/osrm-backend@"
    "sha256:bdfa60e64ae1376bff6ff5605991be50600132a27469a4a9e77c23afd3a6d555"
)


def default_osrm_data_dir() -> Path:
    """Return a platform-appropriate cache location without creating it."""
    import os
    import sys

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "urbanpy" / "osrm"
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "urbanpy" / "osrm"
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "urbanpy" / "osrm"


class OSRMState(StrEnum):
    MISSING = "missing"
    PREPARED = "prepared"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class OSRMConfig(BaseModel):
    """Safe configuration for one local OSRM dataset and service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    region_id: RegionId
    profile: TravelProfile = TravelProfile.DRIVING
    algorithm: Literal["mld"] = "mld"
    bind_host: IPvAnyAddress = IPv4Address("127.0.0.1")
    port: Annotated[StrictInt, Field(ge=1, le=65535)] = 5000
    allow_external: bool = False
    data_dir: Path = Field(default_factory=default_osrm_data_dir)
    image: str = Field(
        default=DEFAULT_OSRM_IMAGE,
        pattern=r"^osrm/osrm-backend@sha256:[0-9a-f]{64}$",
    )
    command_timeout_s: Annotated[float, Field(gt=0)] = 7200.0
    readiness_timeout_s: Annotated[float, Field(gt=0)] = 60.0
    download_timeout_s: Annotated[float, Field(gt=0)] = 120.0
    lock_timeout_s: Annotated[float, Field(gt=0)] = 30.0

    @model_validator(mode="after")
    def require_explicit_external_binding(self) -> Self:
        host: IPv4Address | IPv6Address = self.bind_host
        if not host.is_loopback and not self.allow_external:
            raise ValueError(
                "non-loopback binding requires allow_external=True; local OSRM "
                "has no authentication"
            )
        return self

    @property
    def endpoint(self) -> str:
        host = (
            f"[{self.bind_host}]"
            if self.bind_host.version == 6
            else str(self.bind_host)
        )
        return f"http://{host}:{self.port}"


class OSRMManifest(BaseModel):
    """Identity of one completely prepared immutable dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1] = 1
    region_id: RegionId
    profile: TravelProfile
    algorithm: Literal["mld"]
    pbf_url: HttpUrl
    pbf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pbf_size: Annotated[StrictInt, Field(gt=0)]
    image: str
    created_at: datetime


class OSRMStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: OSRMState
    region_id: RegionId
    profile: TravelProfile
    endpoint: str
    container_name: str
    prepared_dir: Path
    message: str | None = None


class OSRMPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    region_id: RegionId
    profile: TravelProfile
    pbf_url: HttpUrl
    pbf_path: Path
    prepared_dir: Path
    container_name: str
    endpoint: str
    prepare_commands: tuple[tuple[str, ...], ...]
    start_command: tuple[str, ...]
    reusable: bool


class RouteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    distance_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    duration_s: Annotated[float, Field(ge=0, allow_inf_nan=False)]


class TableResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    distances_m: tuple[tuple[float | None, ...], ...]
    durations_s: tuple[tuple[float | None, ...], ...]

    @model_validator(mode="after")
    def require_matching_rectangular_matrices(self) -> Self:
        distance_widths = {len(row) for row in self.distances_m}
        duration_widths = {len(row) for row in self.durations_s}
        if len(distance_widths) > 1 or len(duration_widths) > 1:
            raise ValueError("OSRM table matrices must be rectangular")
        if (
            len(self.distances_m) != len(self.durations_s)
            or distance_widths != duration_widths
        ):
            raise ValueError(
                "distance and duration matrices must have matching dimensions"
            )
        return self


__all__ = [
    "DEFAULT_OSRM_IMAGE",
    "OSRMConfig",
    "OSRMManifest",
    "OSRMPlan",
    "OSRMState",
    "OSRMStatus",
    "RouteResult",
    "TableResult",
    "default_osrm_data_dir",
]
