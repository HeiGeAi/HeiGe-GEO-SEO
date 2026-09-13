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
            with open(out, encoding="utf-8") as fh:
                self.assertIn("OAI-SearchBot", fh.read())

    def test_schema_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "s.html")
            rc = geo_cli.main(["schema", "--type", "article", "--title", "x",
                               "--author", "张三", "--org", "示例", "--out", out])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertIn("Article", fh.read())

    def test_schema_faqpage_needs_qa(self):
        rc = geo_cli.main(["schema", "--type", "faqpage"])
        self.assertEqual(rc, 2)

    def test_schema_faqpage_bad_pair_returns_2(self):
        # 缺 :: 分隔符不再抛 traceback,按参数错误返回 2
        rc = geo_cli.main(["schema", "--type", "faqpage", "--qa", "没有分隔符的问题"])
        self.assertEqual(rc, 2)

    def test_schema_howto_bad_pair_returns_2(self):
        rc = geo_cli.main(["schema", "--type", "howto", "--name", "x",
                           "--step", "没有分隔符的步骤"])
        self.assertEqual(rc, 2)

    def test_hreflang_bad_pair_returns_2(self):
        rc = geo_cli.main(["hreflang", "--locale", "zh-CN"])
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
            with open(out, encoding="utf-8") as fh:
                self.assertIn("# 示例", fh.read())

    def test_bad_json_file_returns_2(self):
        # 畸形 JSON 不再抛 traceback,打印原因并返回 2
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            rc = geo_cli.main(["sov", "--input", bad, "--brand", "品牌A"])
            self.assertEqual(rc, 2)
            rc = geo_cli.main(["measure", "--input", bad, "--brand", "品牌A"])
            self.assertEqual(rc, 2)

    def test_no_subcommand_prints_help(self):
        self.assertEqual(geo_cli.main([]), 0)


if __name__ == "__main__":
    unittest.main()
