import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, scoring, generators  # noqa: E402


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.good = htmldoc.from_file(_path.fixture("good_page.html"))
        self.poor = htmldoc.from_file(_path.fixture("poor_page.html"))

    def test_good_page_passes(self):
        r = scoring.score_document(self.good)
        self.assertGreaterEqual(r["score"], 70)
        self.assertIn(r["grade"], ("良", "优"))
        self.assertEqual(r["vetoes"], [])

    def test_poor_page_veto(self):
        r = scoring.score_document(self.poor)
        self.assertTrue(r["vetoes"])
        self.assertLessEqual(r["score"], 60)
        self.assertEqual(r["grade"], "危急")

    def test_deterministic(self):
        a = scoring.score_document(self.good)
        b = scoring.score_document(self.good)
        self.assertEqual(a["score"], b["score"])
        self.assertEqual(a["dimensions"][0]["earned"], b["dimensions"][0]["earned"])

    def test_faqpage_detected(self):
        r = scoring.score_document(self.good)
        cdim = next(d for d in r["dimensions"] if d["key"] == "C")
        c1 = next(c for c in cdim["checks"] if c["id"] == "C1")
        self.assertEqual(c1["status"], "pass")

    def test_robots_dimension_included_when_provided(self):
        robots = generators.gen_robots("expose-only")
        without = scoring.score_document(self.good)
        with_r = scoring.score_document(self.good, robots_text=robots)
        keys_without = {d["key"] for d in without["dimensions"]}
        keys_with = {d["key"] for d in with_r["dimensions"]}
        self.assertNotIn("A", keys_without)
        self.assertIn("A", keys_with)

    def test_cn_market_uses_baidu(self):
        robots = generators.gen_robots("cn-index")
        r = scoring.score_document(self.good, robots_text=robots, market="cn")
        adim = next(d for d in r["dimensions"] if d["key"] == "A")
        names = " ".join(c["name"] for c in adim["checks"])
        self.assertIn("Baiduspider", names)

    def test_global_market_uses_openai(self):
        robots = generators.gen_robots("expose-only")
        r = scoring.score_document(self.good, robots_text=robots, market="global")
        adim = next(d for d in r["dimensions"] if d["key"] == "A")
        names = " ".join(c["name"] for c in adim["checks"])
        self.assertIn("OpenAI", names)

    def test_blocked_crawlers_lose_points(self):
        blocked = "User-agent: *\nDisallow: /\n"
        r = scoring.score_document(self.good, robots_text=blocked, market="global")
        adim = next(d for d in r["dimensions"] if d["key"] == "A")
        self.assertEqual(adim["earned"], 0)
        self.assertTrue(any("不可被引用" in v for v in r["vetoes"]))

    def test_faq_without_questions_is_flagged(self):
        html = ('<html><body><h1>x</h1><p>'
                + ('内容 ' * 300) +
                '</p><script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"FAQPage"}'
                '</script></body></html>')
        doc = htmldoc.from_string(html)
        r = scoring.score_document(doc)
        self.assertTrue(any("造假" in v for v in r["vetoes"]))


class TestRobotsParse(unittest.TestCase):
    def test_expose_only_blocks_gptbot_allows_search(self):
        robots = scoring.parse_robots(generators.gen_robots("expose-only"))
        self.assertFalse(scoring._ua_allowed(robots, "GPTBot"))
        self.assertTrue(scoring._ua_allowed(robots, "OAI-SearchBot"))

    def test_sitemap_parsed(self):
        robots = scoring.parse_robots(
            generators.gen_robots("allow-all", sitemap="https://x.com/s.xml"))
        self.assertIn("https://x.com/s.xml", robots["sitemaps"])


if __name__ == "__main__":
    unittest.main()
