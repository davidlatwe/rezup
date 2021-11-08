
# Programmatic usage

```python
from rezup import util

# returns a revision from container
revision = util.get_revision()

# resolve package requests with Rez from container
env = util.resolve_environ(revision, ["pkg_a", "pkg_b"])

```

!!! tip "Provisional recipes"

    ```python
    from rezup import util, ContainerRecipe
    
    with ContainerRecipe.provisional_recipes("/to/other/recipes"):
        revision = util.get_revision()
        env = util.resolve_environ(revision, ["pkg_a", "pkg_b"])
    ```
