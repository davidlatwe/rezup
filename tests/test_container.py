
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

        # creates a revision 'apple' to remote side
        self.save_recipe(con_name, data={"description": "apple"})
        container = Container.create(con_name)
        revision = container.new_revision()
        self.assertTrue(container.is_remote())
        self.assertTrue(revision.is_remote())
        self.assertTrue(revision.is_ready())
        self.assertEqual("apple", container.recipe()["description"])
        self.assertEqual("apple", revision.recipe()["description"])

        # shouldn't have any local revision yet
        local = Container.create(con_name, force_local=True)
        local_rev = local.get_latest_revision()
        local_count = len(list(local.iter_revision()))
        self.assertEqual(False, local.is_remote())
        self.assertEqual(None, local_rev)
        self.assertEqual(0, local_count)

        # change container recipe to 'orange'
        self.save_recipe(con_name, data={"description": "orange"})

        # in new session, pull revision from remote and it should be 'apple'
        container = Container.create(con_name)
        revision = container.get_latest_revision()
        pulled_rev = revision.pull()
        self.assertTrue(container.is_remote())
        self.assertEqual(True, revision.is_remote())
        self.assertEqual(False, pulled_rev.is_remote())
        self.assertTrue(revision.is_ready())
        self.assertTrue(pulled_rev.is_ready())
        self.assertEqual("orange", container.recipe()["description"])
        self.assertEqual("apple", revision.recipe()["description"])
        self.assertEqual("apple", pulled_rev.recipe()["description"])

        # now we should have 1 revision 'apple' at local
        local = Container.create(con_name, force_local=True)
        local_rev = local.get_latest_revision()
        local_count = len(list(local.iter_revision()))
        self.assertEqual(False, local.is_remote())
        self.assertEqual(1, local_count)
        self.assertEqual(local_rev.timestamp(), pulled_rev.timestamp())
        self.assertEqual("orange", local.recipe()["description"])
        self.assertEqual("apple", local_rev.recipe()["description"])

    def test_recipe_env(self):
        con_name = "foo"
        self.save_recipe(con_name, {"env": {"bar": "bee"}})

        container = Container.create(con_name)
        revision = container.new_revision()
        env = revision.recipe_env()
        self.assertEqual(env["bar"], "bee")


if __name__ == "__main__":
    unittest.main()
