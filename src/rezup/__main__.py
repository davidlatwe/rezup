
# import sys
# from . import cli
# sys.exit(cli.run())

# testing..
import sys
from .container import Container

container = Container.create("hello")
revision = container.get_latest_revision()
if not revision:
    revision = container.new_revision()
sys.exit(revision.use())
