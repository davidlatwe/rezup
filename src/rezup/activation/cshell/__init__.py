from __future__ import absolute_import, unicode_literals
from pathlib import Path
from ..activator import Activator


class CShellActivator(Activator):
    @classmethod
    def supports(cls, interpreter):
        return interpreter.os != "nt"

    def templates(self):
        yield Path("up.csh")
