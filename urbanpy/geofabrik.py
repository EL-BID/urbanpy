"""Canonical Geofabrik extract discovery.

Identifiers and download URLs come from Geofabrik's published v1 catalog. URLs
are never assembled from user-provided continent or country strings.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any, Final

import requests
from pydantic import ValidationError

from urbanpy._clients.geofabrik import parse_index
from urbanpy.errors import BoundaryValidationError, UrbanPyError
from urbanpy.models import GeofabrikRegion

GEOFABRIK_INDEX_URL: Final = "https://download.geofabrik.de/index-v1-nogeom.json"
DEFAULT_TIMEOUT: Final = (5.0, 30.0)
MAX_CATALOG_BYTES: Final = 5 * 1024 * 1024
USER_AGENT: Final = "urbanpy (+https://github.com/EL-BID/urbanpy)"


class GeofabrikCatalogError(UrbanPyError):
    """The official catalog could not be safely loaded."""


class GeofabrikRegionNotFound(UrbanPyError, LookupError):
    """No canonical ID or ISO alias matched a requested region."""


class GeofabrikRegionAmbiguous(UrbanPyError, LookupError):
    """An ISO alias refers to more than one catalog region."""


class GeofabrikCatalog:
    """An immutable resolver over canonical Geofabrik region records."""

    def __init__(self, regions: Iterable[GeofabrikRegion]) -> None:
        self._regions = tuple(regions)
        self._by_id: dict[str, GeofabrikRegion] = {}
        aliases: defaultdict[str, list[GeofabrikRegion]] = defaultdict(list)

        for region in self._regions:
            canonical_key = region.id.casefold()
            if canonical_key in self._by_id:
                raise GeofabrikCatalogError(
                    f"Duplicate canonical Geofabrik region ID: {region.id}"
                )
            self._by_id[canonical_key] = region
            for alias in (*region.iso_alpha2, *region.iso_3166_2):
                aliases[alias.upper()].append(region)

        self._by_iso = {key: tuple(value) for key, value in aliases.items()}

    @property
    def regions(self) -> tuple[GeofabrikRegion, ...]:
        return self._regions

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "GeofabrikCatalog":
        try:
            return cls(parse_index(payload))
        except ValidationError as error:
            raise BoundaryValidationError.from_pydantic(
                "Geofabrik catalog", error
            ) from error
        except ValueError as error:
            raise GeofabrikCatalogError(str(error)) from error

    @classmethod
    def fetch(
        cls,
        *,
        session: requests.Session | None = None,
        endpoint: str = GEOFABRIK_INDEX_URL,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        max_bytes: int = MAX_CATALOG_BYTES,
    ) -> "GeofabrikCatalog":
        client = session or requests.Session()
        try:
            response = client.get(
                endpoint,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise GeofabrikCatalogError(
                f"Could not fetch the Geofabrik catalog from {endpoint}."
            ) from error

        if len(response.content) > max_bytes:
            raise GeofabrikCatalogError(
                f"Geofabrik catalog exceeds the {max_bytes}-byte safety limit."
            )
        try:
            payload = response.json()
        except requests.JSONDecodeError as error:
            raise GeofabrikCatalogError(
                "Geofabrik catalog response is not valid JSON."
            ) from error
        if not isinstance(payload, Mapping):
            raise GeofabrikCatalogError("Geofabrik catalog JSON must be an object.")
        return cls.from_payload(payload)

    def resolve(self, identifier: str) -> GeofabrikRegion:
        """Resolve an exact catalog ID or ISO 3166 alias.

        Display names and partial final path segments are intentionally not
        aliases. For example, use ``us/california`` or ``US-CA``, not
        ``california``.
        """
        value = identifier.strip()
        if not value:
            raise GeofabrikRegionNotFound(
                "Region is empty; use a canonical Geofabrik ID or ISO 3166 code."
            )

        canonical = self._by_id.get(value.casefold())
        if canonical is not None:
            return canonical

        matches = self._by_iso.get(value.upper(), ())
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            options = ", ".join(region.id for region in matches)
            raise GeofabrikRegionAmbiguous(
                f"ISO alias {value!r} is ambiguous; use one of: {options}."
            )
        raise GeofabrikRegionNotFound(
            f"Unknown Geofabrik region {value!r}; use properties.id from "
            "index-v1-nogeom.json or an advertised ISO 3166 code."
        )


__all__ = [
    "GEOFABRIK_INDEX_URL",
    "GeofabrikCatalog",
    "GeofabrikCatalogError",
    "GeofabrikRegionAmbiguous",
    "GeofabrikRegionNotFound",
]
