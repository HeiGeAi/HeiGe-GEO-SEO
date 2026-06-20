import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402  (sets sys.path)
from lib import htmldoc  # noqa: E402


GOOD = open(_path.fixture("good_page.html"), encoding="utf-8").read()


class TestHtmlDoc(unittest.TestCase):
    def setUp(self):
        self.doc = htmldoc.from_string(GOOD)

    def test_title_and_meta(self):
        self.assertIn("GEO", self.doc.title)
        self.assertIn("description", self.doc.meta)
        self.assertEqual(self.doc.canonical, "https://example.com/geo-guide")
        self.assertEqual(self.doc.lang, "zh-CN")

    def test_headings(self):
        h1 = [h for h in self.doc.headings if h[0] == 1]
        self.assertEqual(len(h1), 1)
        self.assertTrue(any(lvl == 2 for lvl, _ in self.doc.headings))

    def test_jsonld_blocks(self):
        self.assertEqual(len(self.doc.jsonld_blocks), 2)

    def test_counts(self):
        self.assertGreaterEqual(self.doc.counts["table"], 1)
        self.assertGreaterEqual(self.doc.counts["ul"], 1)

    def test_links_external(self):
        ext = self.doc.external_links()
        self.assertTrue(any("arxiv" in lk["href"] for lk in ext))

    def test_cjk_and_wordcount(self):
        self.assertTrue(self.doc.is_cjk)
        self.assertGreater(self.doc.word_count(), 100)

    def test_numbers(self):
        self.assertGreater(self.doc.number_count(), 5)

    def test_empty_shell(self):
        poor = htmldoc.from_file(_path.fixture("poor_page.html"))
        self.assertLess(poor.visible_text_len, 150)


if __name__ == "__main__":
    unittest.main()
