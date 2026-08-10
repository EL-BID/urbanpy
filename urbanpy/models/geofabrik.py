"""Public Geofabrik catalog values."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

RegionId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9/_-]*$")]


class GeofabrikRegion(BaseModel):
    """One canonical extract advertised by Geofabrik's v1 index."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: RegionId
    name: str
    parent: RegionId | None = None
    iso_alpha2: tuple[str, ...] = ()
    iso_3166_2: tuple[str, ...] = ()
    pbf_url: HttpUrl

    @model_validator(mode="after")
    def require_official_pbf_url(self) -> "GeofabrikRegion":
        if self.pbf_url.scheme != "https" or self.pbf_url.host != "download.geofabrik.de":
            raise ValueError(
                "pbf_url must be an HTTPS URL on download.geofabrik.de"
            )
        if not (self.pbf_url.path or "").endswith("-latest.osm.pbf"):
            raise ValueError("pbf_url must identify a latest .osm.pbf extract")
        return self


__all__ = ["GeofabrikRegion"]
