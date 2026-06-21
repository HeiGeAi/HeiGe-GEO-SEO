import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, scoring, report  # noqa: E402


class TestReport(unittest.TestCase):
    def setUp(self):
        self.result = scoring.score_document(
            htmldoc.from_file(_path.fixture("good_page.html")))

    def test_html_self_contained(self):
        html = report.to_html(self.result)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("/100", html)

    def test_sarif_valid_json_and_schema(self):
        result = scoring.score_document(htmldoc.from_file(_path.fixture("poor_page.html")))
        sarif = json.loads(report.to_sarif(result, page_uri="poor.html"))
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"], "HeiGe-GEO-SEO")
        self.assertGreater(len(sarif["runs"][0]["results"]), 0)
        for res in sarif["runs"][0]["results"]:
            self.assertIn(res["level"], ("error", "warning"))

    def test_batch_score_sorts_weakest_first(self):
        b = report.batch_score([_path.fixture("good_page.html"),
                                _path.fixture("poor_page.html")])
        self.assertEqual(b["count"], 2)
        self.assertLessEqual(b["pages"][0]["score"], b["pages"][1]["score"])

    def test_batch_html(self):
        b = report.batch_score([_path.fixture("good_page.html")])
        html = report.batch_to_html(b)
        self.assertIn("批量审计", html)


if __name__ == "__main__":
    unittest.main()
