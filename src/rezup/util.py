
from .container import Container, ContainerError


def locate_rez_lib(container=None):
    """Return Rez lib location form container if found
    Args:
        container (str, optional): container name, look default container
            if name not given
    Returns:
        (Path): rez lib location if found
    """
    name = container or Container.DEFAULT_NAME
    container = Container(name)
    revision = container.get_latest_revision()
    if not revision:
        raise ContainerError("No valid revision in container %r: %s"
                             % (container.name(), container.path()))

    return revision.locate_rez_lib()
