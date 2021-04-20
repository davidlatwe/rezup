from __future__ import absolute_import, unicode_literals
from pathlib import Path
import os
from ..activator import Activator


class BatchActivator(Activator):
    @classmethod
    def supports(cls, interpreter):
        return interpreter.os == "nt"

    def templates(self):
        yield Path("up.bat")

    def instantiate_template(self, replacements, template, creator):
        # ensure the text has all newlines as \r\n - required by batch
        base = super(BatchActivator, self).instantiate_template(replacements, template, creator)
        return base.replace(os.linesep, "\n").replace("\n", os.linesep)
