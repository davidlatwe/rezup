
import time
import unittest
from unittest.mock import patch
from tests.util import TestBase
from rezup._version import __version__
from rezup._vendor.version import Version
from rezup.upgrade import fetch_latest_version_from_pypi, auto_upgrade


def mock_newer_version_from_pypi():
    ver = Version(__version__)
    ver.minor += 9
    ver.patch += 99  # not likely the real version would get there
    return str(ver)


_mock_latest_version = mock_newer_version_from_pypi()
_orig__fetch_from_pypi = fetch_latest_version_from_pypi


class TestUpgrade(TestBase):

    def _test_upgrade(self, m_latest, m_upgrade, m_restart, m_tempdir):
        mock_newer = Version(__version__)
        mock_newer.minor += 1

        m_latest.return_value = str(mock_newer)
        m_tempdir.return_value = self.base

        auto_upgrade()

        m_latest.assert_called_once()
        m_upgrade.assert_called_once()
        m_restart.assert_called_once()

    @patch("tempfile.gettempdir")
    @patch("rezup.upgrade.restart")
    @patch("rezup.upgrade.upgrade")
    @patch("rezup.upgrade.fetch_latest")
    def test_upgrade(self, m_latest, m_upgrade, m_restart, m_tempdir):
        self._test_upgrade(m_latest, m_upgrade, m_restart, m_tempdir)

    @patch("tempfile.gettempdir")
    @patch("rezup.upgrade.restart")
    @patch("rezup.upgrade.upgrade")
    @patch("rezup.upgrade.fetch_latest")
    def test_upgrade_pause(self, m_latest, m_upgrade, m_restart, m_tempdir):
        self._test_upgrade(m_latest, m_upgrade, m_restart, m_tempdir)
        time.sleep(0.5)
        m_latest.side_effect = Exception("Upgrade should be paused.")
        auto_upgrade()

        m_latest.assert_called_once()
        m_upgrade.assert_called_once()
        m_restart.assert_called_once()

    @patch("tempfile.gettempdir")
    @patch("rezup.upgrade.restart")
    @patch("rezup.upgrade.upgrade")
    @patch("rezup.upgrade.fetch_latest")
    @patch("rezup.upgrade._pause_upgrade_period", 2)
    def test_upgrade_resume(self, m_latest, m_upgrade, m_restart, m_tempdir):
        self._test_upgrade(m_latest, m_upgrade, m_restart, m_tempdir)
        time.sleep(0.5)
        m_latest.side_effect = Exception("Upgrade should be paused.")
        auto_upgrade()

        time.sleep(2)  # wait for `_pause_upgrade_period`
        m_latest.side_effect = None

        auto_upgrade()
        self.assertEqual(2, m_latest.call_count)

    @patch("rezup.upgrade._pypi_project",
           "rezup")  # remove this patch once 'rezup-api' is up
    def test_version_fetch_from_pypi(self):
        # as long as the value is not an empty string
        version_str = fetch_latest_version_from_pypi()
        self.assertTrue(bool(version_str))


if __name__ == "__main__":
    unittest.main()
