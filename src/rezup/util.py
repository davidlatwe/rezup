
from .container import Container, ContainerError


def locate_rez_lib(container=None):
    """Return Rez lib location form container if found
    Args:
        container (str, optional): container name, look default container
            if name not given
    Returns:
        (pathlib.Path): rez lib location if found

    Raises:
        ContainerError: when no valid local revision

    """
    name = container or Container.DEFAULT_NAME
    container = Container(name)

    revision = container.get_latest_revision()
    if revision is None:
        raise ContainerError("No valid revision in container %r: %s"
                             % (container.name(), container.path()))

    revision = revision.pull(check_out=False)
    if revision is None:
        raise ContainerError("No matched revision in local container.")

    return revision.locate_rez_lib()
