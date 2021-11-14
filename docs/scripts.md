
# Programmatic usage

```python
from rezup import util

# returns a revision from container
revision = util.get_revision()

# resolve package requests with Rez from container
env = util.resolve_environ(revision, ["pkg_a", "pkg_b"])

```

!!! tip "Provisional recipes"

    By default, all recipe files should be in user home directory and only there will be looked for. But in some cases, you may want to provide your own *remotely*. 

    ```python
    from rezup import util, ContainerRecipe
    
    with ContainerRecipe.provisional_recipes("/to/other/recipes"):
        revision = util.get_revision()
        env = util.resolve_environ(revision, ["pkg_a", "pkg_b"])
    ```
