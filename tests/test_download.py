import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
sys.path.insert(0, SCRIPTS)

import download


class DestinationTests(unittest.TestCase):
    def test_matching_legacy_file_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = b"indexed payload"
            expected = hashlib.sha256(data).hexdigest()
            legacy = os.path.join(tmp, download.safe_filename("o/r", "a/file.yxdb"))
            with open(legacy, "wb") as out:
                out.write(data)

            destination, verified = download.e2_destination(
                tmp, "o/r", "a/file.yxdb", expected
            )

            self.assertEqual(destination, legacy)
            self.assertTrue(verified)

    def test_collision_uses_source_path_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy = os.path.join(tmp, download.safe_filename("o/r", "a/file.yxdb"))
            with open(legacy, "wb") as out:
                out.write(b"another source with the same basename")
            expected = hashlib.sha256(b"indexed payload").hexdigest()

            destination, verified = download.e2_destination(
                tmp, "o/r", "b/file.yxdb", expected
            )

            self.assertNotEqual(destination, legacy)
            self.assertIn("__", os.path.basename(destination))
            self.assertFalse(verified)

    def test_collision_name_preserves_distinct_versions_of_same_source(self):
        first = download.collision_filename("o/r", "a/file.yxdb", "1" * 64)
        second = download.collision_filename("o/r", "a/file.yxdb", "2" * 64)

        self.assertNotEqual(first, second)

    def test_local_payloads_deduplicate_by_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("one.yxdb", "two.yxdb"):
                with open(os.path.join(tmp, name), "wb") as out:
                    out.write(b"same")

            payloads = download.local_payloads(tmp)

            self.assertEqual(list(payloads), [hashlib.sha256(b"same").hexdigest()])


class DownloadTests(unittest.TestCase):
    def test_download_uses_indexed_commit_and_reports_hash_mismatch(self):
        index = {
            "repos": [{
                "repo": "o/r",
                "default_branch": "main",
                "last_checked_sha": "abc123",
                "e2_files": [{
                    "path": "data/file.yxdb",
                    "sha256": hashlib.sha256(b"expected").hexdigest(),
                }],
            }]
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(download, "DOWNLOADS_DIR", tmp):
            with patch.object(download, "download_raw", return_value=b"changed") as raw:
                report = download.download_e2(index, None, False)

        raw.assert_called_once_with("o/r", "data/file.yxdb", "abc123")
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["failures"][0]["reason"], "hash_mismatch")


if __name__ == "__main__":
    unittest.main()
