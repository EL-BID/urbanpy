"""Internal transport schema for Geofabrik's index-v1 catalog."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from urbanpy.models import GeofabrikRegion


class _TransportModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class _Urls(_TransportModel):
    pbf: HttpUrl


class _Properties(_TransportModel):
    region_id: str = Field(alias="id")
    name: str
    parent: str | None = None
    iso_alpha2: list[str] = Field(default_factory=list, alias="iso3166-1:alpha2")
    iso_3166_2: list[str] = Field(default_factory=list, alias="iso3166-2")
    urls: _Urls

    def to_region(self) -> GeofabrikRegion:
        return GeofabrikRegion(
            id=self.region_id,
            name=self.name,
            parent=self.parent,
            iso_alpha2=tuple(self.iso_alpha2),
            iso_3166_2=tuple(self.iso_3166_2),
            pbf_url=self.urls.pbf,
        )


class _Feature(_TransportModel):
    properties: _Properties


class _Index(_TransportModel):
    type: str
    features: list[_Feature]


def parse_index(payload: Any) -> tuple[GeofabrikRegion, ...]:
    index = _Index.model_validate(payload)
    if index.type != "FeatureCollection":
        raise ValueError("Geofabrik index must be a FeatureCollection")
    return tuple(feature.properties.to_region() for feature in index.features)


__all__ = ["parse_index"]
