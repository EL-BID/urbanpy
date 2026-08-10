from importlib.metadata import PackageNotFoundError, version

from . import accessibility, download, geom, models, plotting, routing, utils
from .errors import BoundaryIssue, BoundaryValidationError, UrbanPyError

try:
    __version__ = version("urbanpy")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.3.0a0"

#
# __all__ = []
#
# __all__.extend(download.__all__)
# __all__.extend(geom.__all__)
# __all__.extend(plotting.__all__)
# __all__.extend(routing.__all__)
# __all__.extend(utils.__all__)

__all__ = [
    "__version__",
    "accessibility",
    "BoundaryIssue",
    "BoundaryValidationError",
    "download",
    "geom",
    "models",
    "plotting",
    "routing",
    "utils",
    "UrbanPyError",
]
