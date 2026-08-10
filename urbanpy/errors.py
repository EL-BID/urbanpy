"""Stable UrbanPy exception types and safe boundary-error translation."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError


class UrbanPyError(Exception):
    """Base class for documented UrbanPy failures."""


@dataclass(frozen=True, slots=True)
class BoundaryIssue:
    """One sanitized validation issue without the rejected input value."""

    field_path: str
    message: str
    error_type: str


class BoundaryValidationError(UrbanPyError, ValueError):
    """An invalid public or provider boundary value.

    Full input payloads are intentionally excluded from both the exception text
    and the structured issues so credentials and large provider responses cannot
    leak into logs.
    """

    def __init__(self, category: str, issues: tuple[BoundaryIssue, ...]) -> None:
        self.category = category
        self.issues = issues
        paths = ", ".join(issue.field_path for issue in issues) or "<root>"
        super().__init__(f"Invalid {category} at {paths}.")

    @classmethod
    def from_pydantic(
        cls, category: str, error: ValidationError
    ) -> "BoundaryValidationError":
        issues = tuple(
            BoundaryIssue(
                field_path=_format_location(item["loc"]),
                message=str(item["msg"]),
                error_type=str(item["type"]),
            )
            for item in error.errors(include_input=False, include_url=False)
        )
        return cls(category, issues)


def _format_location(location: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in location) or "<root>"


__all__ = ["BoundaryIssue", "BoundaryValidationError", "UrbanPyError"]
