
import os
import time
import shutil
import unittest
import tempfile
from contextlib import contextmanager
from rezup._vendor import toml


class TestBase(unittest.TestCase):

    def __init__(self, *nargs, **kwargs):
        super(TestBase, self).__init__(*nargs, **kwargs)
        self.test_dir = os.path.dirname(__file__)
        self.base = None
        self.root = None

    def setUp(self):
        base = tempfile.mkdtemp(prefix="rezup_test_")
        root = os.path.join(base, ".local")
        remote = os.path.join(base, ".remote")

        os.environ["REZUP_ROOT_LOCAL"] = root
        os.environ.pop("REZUP_ROOT_REMOTE", None)  # only when needed in test

        self.base = base
        self.root = root
        self.remote = remote

        os.makedirs(root)
        os.makedirs(remote)

    def tearDown(self):
        if os.getenv("REZUP_TEST_KEEP_TMP"):
            print("Tempdir kept due to $REZUP_TEST_KEEP_TMP: %s" % self.root)
            return

        # The retries are here because there is at least one case in the
        # tests where a subproc can be writing to files in a tmpdir after
        # the tests are completed (this is the rez-pkg-cache proc in the
        # test_package_cache:test_caching_on_resolve test).
        #
        retries = 5

        if os.path.exists(self.root):
            for i in range(retries):
                try:
                    shutil.rmtree(self.root)
                    break
                except Exception:
                    if i < (retries - 1):
                        time.sleep(0.2)

    def setup_remote(self):
        os.environ["REZUP_ROOT_REMOTE"] = self.remote

    def save_recipe(self, data, subdir=None):
        level = [self.base, ".recipe"]
        level += [subdir] if subdir else []

        recipe_dir = os.path.join(*level)
        os.makedirs(recipe_dir)

        rezup_toml = os.path.join(recipe_dir, "rezup.toml")
        with open(rezup_toml, "w") as f:
            toml.dump(data, f)

        return rezup_toml


@contextmanager
def temp_env(key, value):
    try:
        os.environ[key] = value
        yield
    finally:
        if key in os.environ:
            del os.environ[key]
