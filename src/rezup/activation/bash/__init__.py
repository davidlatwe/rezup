from __future__ import absolute_import, unicode_literals
from pathlib import Path
from ..activator import Activator


class BashActivator(Activator):
    def templates(self):
        yield Path("up.sh")

    def as_name(self, template):
        return template.stem
