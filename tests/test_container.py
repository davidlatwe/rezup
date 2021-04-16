
import os
import time
import shutil
import unittest
import tempfile
from rezup.container import Container


class TestContainer(unittest.TestCase):

    def __init__(self, *nargs, **kwargs):
        super(TestContainer, self).__init__(*nargs, **kwargs)
        self.root = None

    def setUp(self):
        root = tempfile.mkdtemp(prefix="rezup_test_")
        os.environ["REZUP_ROOT"] = root
        self.root = root

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

    def test_create(self):
        container = Container("foo")
        container.create()

        expected_path = os.path.join(self.root, "foo")
        self.assertTrue(os.path.isdir(expected_path))
