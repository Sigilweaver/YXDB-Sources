import copy
import os
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
sys.path.insert(0, SCRIPTS)

import scan
from detect import E2_MAGIC


def e2_payload(field: str) -> bytes:
    xml = f'<MetaInfo><Field name="{field}" type="Int32" /></MetaInfo>'.encode()
    data = bytearray(100)
    data[: len(E2_MAGIC)] = E2_MAGIC
    struct.pack_into("<I", data, 96, len(xml))
    return bytes(data) + xml


class ScannerIntegrityTests(unittest.TestCase):
    def test_changed_commit_reprocesses_keys_from_prior_run(self):
        known = {"o/r": {"last_checked_sha": "old", "e2_files": []}}
        sources = {"downloaded_keys": ["o/r/a.yxdb", "o/r/b.yxdb"], "errors": []}
        info = {
            "branch": "main",
            "sha": "new",
            "yxdb": [("a.yxdb", 123), ("b.yxdb", 123)],
            "archives": [],
        }
        payloads = [e2_payload("a"), e2_payload("b")]

        with tempfile.TemporaryDirectory() as tmp, patch.object(scan, "DOWNLOADS_DIR", tmp):
            with patch.object(scan, "download_raw", side_effect=payloads) as raw:
                with patch.object(scan.time, "sleep"):
                    scan.process_repo("o/r", info, known, sources)

        self.assertEqual(raw.call_count, 2)
        self.assertEqual(known["o/r"]["last_checked_sha"], "new")
        self.assertEqual(len(known["o/r"]["e2_files"]), 2)

    def test_incomplete_download_preserves_prior_ledger_entry(self):
        known = {"o/r": {"last_checked_sha": "old", "e2_files": [{"path": "old.yxdb"}]}}
        before = copy.deepcopy(known)
        info = {
            "branch": "main",
            "sha": "new",
            "yxdb": [("missing.yxdb", 123)],
            "archives": [],
        }

        with tempfile.TemporaryDirectory() as tmp, patch.object(scan, "DOWNLOADS_DIR", tmp):
            with patch.object(scan, "download_raw", return_value=None):
                scan.process_repo("o/r", info, known, {"downloaded_keys": [], "errors": []})

        self.assertEqual(known, before)

    def test_truncated_tree_preserves_prior_ledger_entry(self):
        known = {"o/r": {"last_checked_sha": "old", "e2_files": [{"path": "old.yxdb"}]}}
        before = copy.deepcopy(known)
        responses = [
            {"default_branch": "main"},
            {"object": {"sha": "new"}},
            {"tree": [], "truncated": True},
        ]

        with patch.object(scan, "gh_api", side_effect=responses):
            result = scan.check_repo("o/r", known, {})

        self.assertEqual(result["status"], "tree_truncated")
        self.assertEqual(known, before)


if __name__ == "__main__":
    unittest.main()
