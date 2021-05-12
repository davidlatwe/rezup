
import os
from rezup.container import Container
from rezup._vendor import toml
from .util import TestBase


class TestContainer(TestBase):

    def __init__(self, *nargs, **kwargs):
        super(TestContainer, self).__init__(*nargs, **kwargs)
        self.rezup_toml = None
        self.recipe = {
            "rez": {
                "name": "rez",
                "url": os.path.join(self.test_dir, "mock", "rez"),
            }
        }

    def setUp(self):
        super(TestContainer, self).setUp()
        self.rezup_toml = os.path.join(self.base, "rezup.toml")

        with open(self.rezup_toml, "w") as f:
            toml.dump(self.recipe, f)

    def test_create(self):
        container = Container.create("foo")

        expected_path = os.path.join(self.root, "foo")
        self.assertTrue(os.path.isdir(expected_path))
        self.assertTrue(container.is_exists())
        self.assertTrue(container.is_empty())

    def test_create_revision(self):
        container = Container.create("foo")
        revision = container.new_revision(recipe_file=self.rezup_toml)

        self.assertTrue(revision.is_valid())
        self.assertTrue(revision.is_ready())
