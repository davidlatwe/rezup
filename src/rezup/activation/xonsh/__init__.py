from __future__ import absolute_import, unicode_literals
from pathlib import Path
from ..activator import Activator


class XonshActivator(Activator):
    def templates(self):
        yield Path("up.xsh")

    @classmethod
    def supports(cls, interpreter):
        return interpreter.version_info >= (3, 5)
