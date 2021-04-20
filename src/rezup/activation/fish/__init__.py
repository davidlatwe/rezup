from __future__ import absolute_import, unicode_literals
from pathlib import Path
from ..activator import Activator


class FishActivator(Activator):
    def templates(self):
        yield Path("up.fish")
