#!/usr/bin/env python3
"""Regression guard for committed case outputs.

The case runner is also the generator for the checked-in examples.  A green
run is not enough: the generated files must match what users see in Git.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def case_output_files(cases_root):
    files = set()
    results = cases_root / "RESULTS.md"
    if results.is_file():
        files.add(results.relative_to(cases_root))
    files.update(
        path.relative_to(cases_root)
        for path in cases_root.glob("case-*/output/**/*")
        if path.is_file()
    )
    return files


class CaseOutputSyncTests(unittest.TestCase):
    def test_stale_committed_output_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "repo"
            fake_cases = fake_root / "cases"
            fake_output = fake_cases / "case-01" / "output"
            fake_scripts = fake_root / "scripts"
            fake_output.mkdir(parents=True)
            fake_scripts.mkdir(parents=True)

            (fake_cases / "RESULTS.md").write_text("current\n", encoding="utf-8")
            (fake_output / "current.txt").write_text("current\n", encoding="utf-8")
            (fake_output / "stale.txt").write_text("stale\n", encoding="utf-8")
            (fake_cases / "run_cases.py").write_text(
                "from pathlib import Path\n"
                "here = Path(__file__).resolve().parent\n"
                "(here / 'RESULTS.md').write_text('current\\n', encoding='utf-8')\n"
                "output = here / 'case-01' / 'output'\n"
                "output.mkdir(parents=True, exist_ok=True)\n"
                "(output / 'current.txt').write_text('current\\n', encoding='utf-8')\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            original_root = globals()["ROOT"]
            try:
                globals()["ROOT"] = fake_root
                CaseOutputSyncTests(
                    "test_committed_case_outputs_match_current_generator"
                ).run(result)
            finally:
                globals()["ROOT"] = original_root

        self.assertFalse(
            result.wasSuccessful(),
            "a committed output that the generator no longer writes must be reported",
        )
        details = "\n".join(
            traceback for _, traceback in result.failures + result.errors
        )
        self.assertIn("case-01/output/stale.txt", details)

    def test_committed_case_outputs_match_current_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            temp_cases = temp_root / "cases"
            shutil.copytree(ROOT / "cases", temp_cases)
            shutil.copytree(ROOT / "scripts", temp_root / "scripts")
            for output_dir in temp_cases.glob("case-*/output"):
                shutil.rmtree(output_dir)

            proc = subprocess.run(
                [sys.executable, str(temp_cases / "run_cases.py")],
                cwd=temp_cases,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            expected_root = ROOT / "cases"
            expected_files = case_output_files(expected_root)
            generated_files = case_output_files(temp_cases)
            mismatches = sorted(str(path) for path in expected_files ^ generated_files)
            for relative in sorted(expected_files & generated_files):
                expected = expected_root / relative
                actual = temp_cases / relative
                if expected.read_bytes() != actual.read_bytes():
                    mismatches.append(str(relative))

            self.assertEqual(
                mismatches,
                [],
                "case outputs are stale; run `cd cases && python3 run_cases.py`: "
                + ", ".join(mismatches),
            )


if __name__ == "__main__":
    unittest.main()
