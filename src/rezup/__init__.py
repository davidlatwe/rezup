
try:
    from ._version import __version__
except ImportError:
    __version__ = None  # not installed

from .container import Container, Revision, iter_containers
from .recipe import ContainerRecipe
from .exceptions import ContainerError


def get_rezup_version():
    # type: () -> str
    import sys
    return "{name} {ver} from {lib} (python {x}.{y})".format(
        name="rezup",
        ver=__version__ or "(not installed)",
        lib=__path__[0],
        x=sys.version_info.major,
        y=sys.version_info.minor,
    )


__all__ = (
    "__version__",
    "Container",
    "Revision",
    "ContainerRecipe",
    "ContainerError",
    "iter_containers",
    "get_rezup_version",
)
