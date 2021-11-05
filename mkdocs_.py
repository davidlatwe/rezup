#!/usr/bin/env python3
import shutil
from pathlib import Path
from pdoc import pdoc, render

here = Path(__file__).parent
out = here / "docs" / "api"
if out.is_dir():
    shutil.rmtree(out)

# Render pdoc's documentation into docs/api...
render.configure(
    template_directory=here / "pdoc-template",
    docformat="google",
)
pdoc(
    "rezup",
    "rezup.util",
    "rezup.cli",
    output_directory=out
)

# ...and rename the .html files to .md so that mkdocs picks them up!
for f in out.glob("**/*.html"):
    f.rename(f.with_suffix(".md"))
