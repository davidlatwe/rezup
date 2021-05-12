
import os
import time
import shutil
import unittest
import tempfile


class TestBase(unittest.TestCase):

    def __init__(self, *nargs, **kwargs):
        super(TestBase, self).__init__(*nargs, **kwargs)
        self.test_dir = os.path.dirname(__file__)
        self.base = None
        self.root = None

    def setUp(self):
        base = tempfile.mkdtemp(prefix="rezup_test_")
        root = os.path.join(base, ".rezup")
        os.environ["REZUP_ROOT_LOCAL"] = root
        self.base = base
        self.root = root

        os.makedirs(root)

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
