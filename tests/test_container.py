
import os
import unittest
from rezup.container import Container
from tests.util import TestBase


class TestContainer(TestBase):

    def test_create(self):
        con_name = "foo"
        container = Container.create(con_name)
        expected_path = os.path.join(self.root, con_name)

        self.assertFalse(os.path.isdir(expected_path))
        self.assertFalse(container.is_exists())
        self.assertTrue(container.is_empty())

        self.save_recipe(con_name)
        container.new_revision()

        self.assertTrue(os.path.isdir(expected_path))
        self.assertTrue(container.is_exists())
        self.assertFalse(container.is_empty())

    def test_create_revision(self):
        con_name = "foo"
        self.save_recipe(con_name)

        container = Container.create(con_name)
        revision = container.new_revision()

        self.assertTrue(revision.is_valid())
        self.assertTrue(revision.is_ready())

    def test_revision_from_remote(self):
        con_name = "foo"
        self.setup_remote()

        container = Container.create(con_name)
        self.assertTrue(container.is_remote())

        self.save_recipe(con_name)
        revision = container.new_revision()

        self.assertTrue(revision.is_valid())
        self.assertTrue(revision.is_ready())
        self.assertTrue(revision.is_remote())

        pulled_rev = revision.pull()

        local = Container.create(con_name, force_local=True)
        self.assertFalse(local.is_remote())

        local_rev = local.get_latest_revision()

        self.assertEqual(pulled_rev.timestamp(), local_rev.timestamp())


if __name__ == "__main__":
    unittest.main()
