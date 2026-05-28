"""Tests for src.utils.paths.reanchor_my_drive_path — Rule 7 contract + behavior."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.paths import reanchor_my_drive_path


CURRENT_ROOT = r"C:\Users\Michaels Alienware\My Drive"
OLD_ROOT = r"C:\Users\mperr\My Drive"


def _assert_contract(test, result):
    test.assertIn(result['status'], ('success', 'skipped', 'error'))
    test.assertIn('data', result)
    test.assertIn('error_type', result)
    test.assertIn('error_message', result)
    test.assertIn('duration_ms', result)
    test.assertIsInstance(result['duration_ms'], int)
    test.assertGreaterEqual(result['duration_ms'], 0)


class ReanchorMyDrivePathTests(unittest.TestCase):

    def test_swaps_old_user_prefix_to_current(self):
        old = OLD_ROOT + r"\Python Programs\Setting Up Python Routines\Routines\PlaySilvaMeditation.json"
        result = reanchor_my_drive_path(old, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'success')
        expected = os.path.normpath(
            CURRENT_ROOT + r"\Python Programs\Setting Up Python Routines\Routines\PlaySilvaMeditation.json"
        )
        self.assertEqual(result['data']['path'], expected)
        self.assertEqual(result['data']['original'], old)

    def test_forward_slash_input(self):
        old = "C:/Users/mperr/My Drive/Python Programs/foo.mp3"
        result = reanchor_my_drive_path(old, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['data']['path'].endswith(os.path.normpath("My Drive/Python Programs/foo.mp3")))

    def test_idempotent_when_already_correct(self):
        already = CURRENT_ROOT + r"\Python Programs\foo.mp3"
        result = reanchor_my_drive_path(already, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['path'], os.path.normpath(already))

    def test_skipped_when_no_my_drive(self):
        local = r"D:\Music\track.mp3"
        result = reanchor_my_drive_path(local, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['data']['path'], local)
        self.assertEqual(result['data']['reason'], 'no_my_drive_anchor')

    def test_skipped_does_not_match_substring(self):
        misleading = r"C:\Users\x\My Driveful\foo"
        result = reanchor_my_drive_path(misleading, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'skipped')

    def test_bare_my_drive_root_path(self):
        bare = OLD_ROOT
        result = reanchor_my_drive_path(bare, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['path'], os.path.normpath(CURRENT_ROOT))

    def test_error_on_non_string(self):
        result = reanchor_my_drive_path(None, current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'TypeError')

    def test_error_on_empty_string(self):
        result = reanchor_my_drive_path("", current_my_drive_root=CURRENT_ROOT)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'error')

    def test_autodetects_current_root_when_omitted(self):
        old = OLD_ROOT + r"\foo\bar.txt"
        result = reanchor_my_drive_path(old)
        _assert_contract(self, result)
        self.assertEqual(result['status'], 'success')
        expected_root = os.path.join(os.path.expanduser('~'), 'My Drive')
        self.assertTrue(result['data']['path'].startswith(os.path.normpath(expected_root)))


if __name__ == '__main__':
    unittest.main()
