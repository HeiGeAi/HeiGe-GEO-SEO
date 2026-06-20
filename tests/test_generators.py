import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import generators  # noqa: E402


class TestRobots(unittest.TestCase):
    def test_allow_all_contains_key_bots(self):
        out = generators.gen_robots("allow-all")
        for ua in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot",
                   "Googlebot", "Baiduspider"):
            self.assertIn(ua, out)

    def test_expose_only_disallows_training(self):
        out = generators.gen_robots("expose-only")
        self.assertIn("User-agent: GPTBot\nDisallow: /", out)
        self.assertIn("User-agent: OAI-SearchBot\nAllow: /", out)

    def test_cn_index_has_baidu_sogou(self):
        out = generators.gen_robots("cn-index")
        self.assertIn("Baiduspider", out)
        self.assertIn("Sogou web spider", out)

    def test_sitemap_line(self):
        out = generators.gen_robots("allow-all", sitemap="https://x.com/s.xml")
        self.assertIn("Sitemap: https://x.com/s.xml", out)

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            generators.gen_robots("nope")


class TestSchema(unittest.TestCase):
    def test_article_valid_json_with_trust_chain(self):
        node = generators.gen_article(
            "标题", author="张三", org="示例科技", url="https://x.com/a",
            date_published="2026-06-20", author_url="https://x.com/about#a",
            same_as=["https://linkedin.com/in/x"])
        self.assertEqual(node["@type"], "Article")
        self.assertEqual(node["author"]["@id"], "https://x.com/about#a")
        self.assertEqual(node["dateModified"], "2026-06-20")
        json.dumps(node)  # must serialize

    def test_faqpage_structure(self):
        node = generators.gen_faqpage([("问1", "答1"), ("问2", "答2")])
        self.assertEqual(len(node["mainEntity"]), 2)
        self.assertEqual(node["mainEntity"][0]["acceptedAnswer"]["text"], "答1")

    def test_howto_positions(self):
        node = generators.gen_howto("做法", [("步骤一", "做A"), ("步骤二", "做B")])
        self.assertEqual(node["step"][1]["position"], 2)

    def test_product_offer_and_rating(self):
        node = generators.gen_product("产品", price=99, rating=4.8, rating_count=120)
        self.assertEqual(node["offers"]["price"], "99")
        self.assertEqual(node["aggregateRating"]["ratingCount"], "120")

    def test_to_script_wraps(self):
        s = generators.to_script(generators.gen_faqpage([("q", "a")]))
        self.assertTrue(s.startswith('<script type="application/ld+json">'))
        self.assertIn("FAQPage", s)


class TestLlms(unittest.TestCase):
    def test_structure(self):
        out = generators.gen_llms_txt(
            "示例科技", "一句话简介",
            sections=[{"title": "Docs", "links": [
                {"name": "开始", "url": "https://x.com/s", "desc": "5分钟"}]}])
        self.assertIn("# 示例科技", out)
        self.assertIn("> 一句话简介", out)
        self.assertIn("## Docs", out)
        self.assertIn("- [开始](https://x.com/s): 5分钟", out)

    def test_parse_links_file(self):
        text = "https://x.com/a | 名称A | 描述A\nhttps://x.com/b | 名称B\n# 注释\n"
        links = generators.parse_links_file(text)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["desc"], "描述A")
        self.assertIsNone(links[1]["desc"])


if __name__ == "__main__":
    unittest.main()
