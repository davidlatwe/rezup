
# import sys
# from . import cli
# sys.exit(cli.run())

# testing..
import sys
from .container import Container

container = Container.create("hello")
layer = container.get_latest_layer()
if not layer:
    layer = container.new_layer()
sys.exit(layer.use())
