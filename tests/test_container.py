
import os
import unittest
from rezup.container import Container
from tests.util import TestBase


class TestContainer(TestBase):

    def test_create(self):
        container = Container.create("foo")

        expected_path = os.path.join(self.root, "foo")
        self.assertTrue(os.path.isdir(expected_path))
        self.assertTrue(container.is_exists())
        self.assertTrue(container.is_empty())

    def test_create_revision(self):
        mock_rez = os.path.join(self.test_dir, "mock", "rez")
        recipe = {"rez": {"name": "rez", "url": mock_rez}}
        rezup_toml = self.save_recipe(recipe)

        container = Container.create("foo")
        revision = container.new_revision(recipe_file=rezup_toml)

        self.assertTrue(revision.is_valid())
        self.assertTrue(revision.is_ready())

    def test_revision_from_remote(self):
        self.setup_remote()

        container = Container.create("foo")
        self.assertTrue(container.is_remote())

        mock_rez = os.path.join(self.test_dir, "mock", "rez")
        recipe = {"rez": {"name": "rez", "url": mock_rez}}
        rezup_toml = self.save_recipe(recipe)

        revision = container.new_revision(recipe_file=rezup_toml)
        self.assertTrue(revision.is_valid())
        self.assertTrue(revision.is_ready())
        self.assertTrue(revision.is_remote())

        pulled_rev = revision.pull()

        local = Container.create("foo", root=Container.local_root())
        self.assertFalse(local.is_remote())

        local_rev = local.get_latest_revision()

        self.assertEqual(pulled_rev.timestamp(), local_rev.timestamp())


if __name__ == "__main__":
    unittest.main()
