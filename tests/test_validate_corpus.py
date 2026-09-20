import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "validate_corpus", pathlib.Path(__file__).parents[1] / "scripts" / "validate_corpus.py"
)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class BaselineTests(unittest.TestCase):
    def test_known_error_requires_exact_reviewed_signature(self):
        expected = {"status": "decode_error", "error_type": "ValueError", "error": "record 7"}
        self.assertEqual(validation.compare({"a": expected}, {"a": expected}), [])
        self.assertTrue(validation.compare({"a": {**expected, "error": "record 8"}}, {"a": expected}))
        self.assertTrue(validation.compare({"a": expected}, None))

    def test_timeouts_and_crashes_cannot_be_baselined(self):
        for status in ("timeout", "crash", "runner_error", "count_mismatch"):
            result = {"a": {"status": status}}
            self.assertTrue(validation.compare(result, result))

    def test_changed_values_and_missing_inputs_fail(self):
        previous = {"status": "ok", "values_sha256": "old"}
        self.assertTrue(validation.compare({"a": {**previous, "values_sha256": "new"}}, {"a": previous}))
        self.assertTrue(validation.compare({}, {"a": previous}))
        self.assertTrue(validation.compare({"a": previous}, {}))

    def test_relocation_and_timing_do_not_change_signature(self):
        a = {"status": "ok", "seconds": 1, "paths": ["old"]}
        b = {"status": "ok", "seconds": 2, "paths": ["new"]}
        self.assertEqual(validation.compare({"a": a}, {"a": b}), [])

    def test_timeout_is_reported_and_run_continues(self):
        with patch.object(validation.subprocess, "run", side_effect=subprocess.TimeoutExpired("reader", 1)):
            result = validation.run_one("sigilyx", pathlib.Path("fixture.yxdb"), "python", 1, None)
        self.assertEqual(result["status"], "timeout")

    def test_worker_process_decodes_and_checks_declared_count(self):
        with tempfile.TemporaryDirectory() as directory:
            module = pathlib.Path(directory) / "sigilyx.py"
            module.write_text(
                "def record_count(path): return 3 if 'mismatch' in path else 2\n"
                "class Frame:\n"
                "    height = 2\n"
                "    columns = ['value']\n"
                "    def iter_rows(self): return iter([(17,), (None,)])\n"
                "def read_yxdb(path, spatial): return Frame()\n"
            )
            result = validation.run_one("sigilyx", pathlib.Path("fixture.yxdb"), sys.executable, 5, directory)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["rows"], 2)
            self.assertEqual(len(result["values_sha256"]), 64)
            mismatch = validation.run_one("sigilyx", pathlib.Path("mismatch.yxdb"), sys.executable, 5, directory)
            self.assertEqual(mismatch["status"], "count_mismatch")
            self.assertEqual(mismatch["declared"], 3)
            self.assertEqual(mismatch["rows"], 2)

    def test_worker_import_failure_is_not_a_decode_error(self):
        with tempfile.TemporaryDirectory() as directory:
            (pathlib.Path(directory) / "sigilyx.py").write_text("raise ImportError('missing extension')\n")
            result = validation.run_one("sigilyx", pathlib.Path("fixture.yxdb"), sys.executable, 5, directory)
        self.assertEqual(result["status"], "crash")
        self.assertIn("missing extension", result["error"])

    def test_sigilyx_conversion_type_error_is_a_decode_error(self):
        with tempfile.TemporaryDirectory() as directory:
            (pathlib.Path(directory) / "sigilyx.py").write_text(
                "def record_count(path): return 1\n"
                "def read_yxdb(path, spatial): raise TypeError('data conversion error: record 0')\n"
            )
            result = validation.run_one("sigilyx", pathlib.Path("fixture.yxdb"), sys.executable, 5, directory)
        self.assertEqual(result["status"], "decode_error")
        self.assertEqual(result["error_type"], "TypeError")

    def test_canonical_encoding_preserves_important_distinctions(self):
        self.assertNotEqual(validation.canonical(0.0), validation.canonical(-0.0))
        self.assertNotEqual(validation.canonical(b"abc"), validation.canonical("abc"))
        self.assertNotEqual(validation.canonical(float("nan")), validation.canonical(None))
        with self.assertRaises(TypeError):
            validation.canonical(object())


if __name__ == "__main__":
    unittest.main()
