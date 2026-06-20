import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
import geo_cli  # noqa: E402


class TestCli(unittest.TestCase):
    def test_score_good_passes_threshold(self):
        rc = geo_cli.main(["score", "--input", _path.fixture("good_page.html"),
                           "--fail-under", "70", "--json"])
        self.assertEqual(rc, 0)

    def test_score_poor_fails_threshold(self):
        rc = geo_cli.main(["score", "--input", _path.fixture("poor_page.html"),
                           "--fail-under", "70", "--json"])
        self.assertEqual(rc, 1)

    def test_robots_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "robots.txt")
            rc = geo_cli.main(["robots", "--strategy", "expose-only", "--out", out])
            self.assertEqual(rc, 0)
            self.assertIn("OAI-SearchBot", open(out, encoding="utf-8").read())

    def test_schema_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "s.html")
            rc = geo_cli.main(["schema", "--type", "article", "--title", "x",
                               "--author", "张三", "--org", "示例", "--out", out])
            self.assertEqual(rc, 0)
            self.assertIn("Article", open(out, encoding="utf-8").read())

    def test_schema_faqpage_needs_qa(self):
        rc = geo_cli.main(["schema", "--type", "faqpage"])
        self.assertEqual(rc, 2)

    def test_llms_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            links = os.path.join(tmp, "links.txt")
            with open(links, "w", encoding="utf-8") as fh:
                fh.write("https://x.com/a | 开始 | 5分钟\n")
            out = os.path.join(tmp, "llms.txt")
            rc = geo_cli.main(["llms", "--site", "示例", "--summary", "简介",
                               "--links", links, "--out", out])
            self.assertEqual(rc, 0)
            self.assertIn("# 示例", open(out, encoding="utf-8").read())

    def test_no_subcommand_prints_help(self):
        self.assertEqual(geo_cli.main([]), 0)


if __name__ == "__main__":
    unittest.main()
