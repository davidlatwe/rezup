__version__ = "1.13.0"


def package_info():
    import rezup
    return dict(
        name=rezup.__package__,
        version=__version__,
        path=rezup.__path__[0],
    )


def print_info():
    import sys
    info = package_info()
    py = sys.version_info
    print(info["name"],
          info["version"],
          "from", info["path"],
          "(python {x}.{y})".format(x=py.major, y=py.minor))
