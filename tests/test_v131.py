"""v1.3.1 回归测试:专家审查挖出的 bug + 边界 + 补的 AEO schema。"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, sov, scoring, diagnose, generators  # noqa: E402
from lib import platform_recommend as pr  # noqa: E402


class TestBugFixes(unittest.TestCase):
    def test_number_count_excludes_dates(self):
        d = htmldoc.from_string("<p>更新于 2025-06-22,见 https://x.com</p>")
        self.assertEqual(d.number_count(), 0)

    def test_number_count_excludes_versions(self):
        d = htmldoc.from_string("<p>版本 v1.2.3 发布</p>")
        self.assertEqual(d.number_count(), 0)

    def test_number_count_keeps_real_stats(self):
        d = htmldoc.from_string("<p>39 元,2 万作者,降到 1 分钟</p>")
        self.assertGreaterEqual(d.number_count(), 3)

    def test_domain_strips_www_only(self):
        self.assertEqual(sov._domain("www.baidu.com"), "baidu.com")

    def test_domain_does_not_eat_leading_w(self):
        self.assertEqual(sov._domain("webflow.com"), "webflow.com")
        self.assertEqual(sov._domain("wow.com"), "wow.com")
        self.assertEqual(sov._domain("web.example.com"), "web.example.com")

    def test_citation_sov_attribution_correct_after_fix(self):
        recs = [{"prompt": "q", "engine": "e",
                 "answer": "见 https://webflow.com/a 和 https://other.com/b"}]
        r = sov.analyze(recs, "Webflow", brand_domain="webflow.com")
        self.assertEqual(r["citation_sov"]["Webflow"], 50.0)

    def test_reverse_rejects_single_char(self):
        self.assertEqual(pr.reverse("网")["engine_count"], 0)

    def test_reverse_still_matches_real_platform(self):
        self.assertGreaterEqual(pr.reverse("知乎")["engine_count"], 4)


class TestBoundaries(unittest.TestCase):
    def test_empty_html_scores_without_crash(self):
        r = scoring.score_document(htmldoc.from_string(""))
        self.assertIsInstance(r["score"], int)

    def test_malformed_html_no_crash(self):
        r = scoring.score_document(htmldoc.from_string("<p><div><h1>x</h1"))
        self.assertIsInstance(r["score"], int)

    def test_empty_records_sov(self):
        r = sov.analyze([], "Acme")
        self.assertEqual(r["coverage"]["total"], 0)

    def test_diagnose_empty(self):
        r = diagnose.diagnose(htmldoc.from_string(""))
        self.assertIn("findings", r)

    def test_recommend_unknown_engine_no_crash(self):
        r = pr.recommend(["nonexistent-engine"])
        self.assertEqual(r["recommendations"], [])


class TestNewSchemas(unittest.TestCase):
    def test_breadcrumb(self):
        node = generators.gen_breadcrumb([("首页", "https://x.com/"), ("文章",)])
        self.assertEqual(node["@type"], "BreadcrumbList")
        self.assertEqual(len(node["itemListElement"]), 2)
        self.assertNotIn("item", node["itemListElement"][1])  # 末项无 url
        json.dumps(node)

    def test_itemlist(self):
        node = generators.gen_itemlist("最好的X", [("A", "https://x.com/a"), ("B", None)])
        self.assertEqual(node["@type"], "ItemList")
        self.assertEqual(node["itemListElement"][0]["position"], 1)

    def test_itemlist_embeds_product(self):
        prod = generators.gen_product("智能排版器", price=39)
        node = generators.gen_itemlist("榜单", [prod])
        self.assertEqual(node["itemListElement"][0]["item"]["@type"], "Product")

    def test_review(self):
        node = generators.gen_review("智能排版器", 4.8, "黑哥", body="好用")
        self.assertEqual(node["@type"], "Review")
        self.assertEqual(node["reviewRating"]["ratingValue"], "4.8")

    def test_graph_links_nodes(self):
        node = generators.gen_graph(
            generators.gen_article("标题", author="黑哥", org="示例"),
            generators.gen_organization("示例", url="https://x.com"))
        self.assertEqual(node["@context"], "https://schema.org")
        self.assertEqual(len(node["@graph"]), 2)
        # 子节点不再各自带 @context
        for n in node["@graph"]:
            self.assertNotIn("@context", n)
        json.dumps(node)

    def test_graph_skips_none(self):
        node = generators.gen_graph(generators.gen_review("X", 5, "a"), None)
        self.assertEqual(len(node["@graph"]), 1)


if __name__ == "__main__":
    unittest.main()
