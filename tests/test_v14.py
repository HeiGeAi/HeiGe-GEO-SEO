"""v1.4 测试:SEO 偏科补强(意图/hreflang/D5质量)+ 国内工具化(百度推送/神马360/cn评分)。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import intent, generators, scoring, htmldoc, attribution  # noqa: E402


class TestIntent(unittest.TestCase):
    def test_commercial(self):
        r = intent.classify("最好的公众号排版工具对比")
        self.assertEqual(r["intent"], "commercial")
        self.assertIn("ItemList", r["recommended_schema"])

    def test_transactional(self):
        r = intent.classify("智能排版器多少钱 价格")
        self.assertEqual(r["intent"], "transactional")

    def test_informational(self):
        r = intent.classify("什么是 GEO 怎么做")
        self.assertEqual(r["intent"], "informational")

    def test_navigational(self):
        r = intent.classify("黑哥AI 官网 登录")
        self.assertEqual(r["intent"], "navigational")

    def test_no_signal_defaults_informational(self):
        r = intent.classify("公众号排版器")
        self.assertEqual(r["intent"], "informational")
        self.assertEqual(r["confidence"], "low")

    def test_english(self):
        r = intent.classify("best seo tools comparison")
        self.assertEqual(r["intent"], "commercial")

    def test_render(self):
        self.assertIn("搜索意图分类", intent.render(intent.classify("怎么做")))


class TestHreflang(unittest.TestCase):
    def test_generates_alternates(self):
        out = generators.gen_hreflang([("zh-CN", "https://x.com/"),
                                       ("en", "https://x.com/en/")],
                                      x_default="https://x.com/")
        self.assertIn('hreflang="zh-CN"', out)
        self.assertIn('hreflang="x-default"', out)
        self.assertEqual(out.count("hreflang"), 3)


class TestBaiduPush(unittest.TestCase):
    def test_contains_curl_and_urls(self):
        out = generators.gen_baidu_push("xsbbai.com", "TOK",
                                        ["https://xsbbai.com/a", "https://xsbbai.com/b"])
        self.assertIn("data.zz.baidu.com/urls", out)
        self.assertIn("site=xsbbai.com", out)
        self.assertIn("token=TOK", out)
        self.assertIn("https://xsbbai.com/a", out)

    def test_fast_mode(self):
        out = generators.gen_baidu_push("x.com", "T", ["https://x.com/a"], fast=True)
        self.assertIn("快速收录", out)


class TestCnScoringFix(unittest.TestCase):
    def test_cn_llms_not_over_penalized(self):
        robots = generators.gen_robots("cn-index")
        doc = htmldoc.from_file(_path.fixture("good_page.html"))
        r = scoring.score_document(doc, robots_text=robots, market="cn")
        bdim = next(d for d in r["dimensions"] if d["key"] == "B")
        b1 = next(c for c in bdim["checks"] if c["id"] == "B1")
        self.assertEqual(b1["earned"], 4)  # 不重罚,给 4/8

    def test_global_llms_still_penalized(self):
        robots = generators.gen_robots("expose-only")
        doc = htmldoc.from_file(_path.fixture("good_page.html"))
        r = scoring.score_document(doc, robots_text=robots, market="global")
        bdim = next(d for d in r["dimensions"] if d["key"] == "B")
        b1 = next(c for c in bdim["checks"] if c["id"] == "B1")
        self.assertEqual(b1["earned"], 0)  # 海外仍按缺失算


class TestD5Authority(unittest.TestCase):
    def test_authoritative_outbound_in_note(self):
        html = ("<html><body><h1>x</h1><p>" + ("内容 " * 200) +
                "数字 39 元 2 万 1 倍,见 <a href='https://zh.wikipedia.org/wiki/x'>维基</a></p></body></html>")
        r = scoring.score_document(htmldoc.from_string(html))
        ddim = next(d for d in r["dimensions"] if d["key"] == "D")
        d5 = next(c for c in ddim["checks"] if c["id"] == "D5")
        self.assertIn("权威外链", d5["note"])


class TestCnCrawlers(unittest.TestCase):
    def test_360_classified_cn(self):
        log = '1.1.1.1 - - [x] "GET /a HTTP/1.1" 200 1 "-" "x 360Spider y"\n'
        r = attribution.parse_access_log(log)
        self.assertEqual(r["by_region"]["cn"], 1)

    def test_cn_index_robots_has_shenma_360(self):
        out = generators.gen_robots("cn-index")
        self.assertIn("YisouSpider", out)
        self.assertIn("360Spider", out)


class TestV14ReviewFixes(unittest.TestCase):
    """复审挖出的问题的回归测试。"""

    def test_cn_bad_llms_not_below_no_llms(self):
        # 倒挂修复:cn 提供烂 llms.txt(无H1)>= 不提供(4)
        bad = scoring._dim_B(None, "just text no h1", False, False, "cn")
        none = scoring._dim_B(None, None, False, False, "cn")
        self.assertGreaterEqual(bad["checks"][0]["earned"], none["checks"][0]["earned"])

    def test_baidu_push_sanitizes_injection(self):
        out = generators.gen_baidu_push(
            "x.com", 'tok";rm -rf ~ #',
            ["https://x.com/a", "EOF", "https://x.com/$(whoami)", "; rm -rf /"])
        self.assertNotIn('";rm -rf', out)        # token 被编码
        self.assertNotIn("$(whoami)", out)        # 恶意 url 丢弃
        self.assertIn("https://x.com/a", out)     # 干净 url 保留
        self.assertIn("已丢弃 3 条", out)

    def test_baidu_push_fast_honest(self):
        out = generators.gen_baidu_push("x.com", "T", ["https://x.com/a"], fast=True)
        self.assertIn("已基本下线", out)

    def test_intent_english_word_boundary(self):
        self.assertNotEqual(intent.classify("whichever option")["intent"], "commercial")
        self.assertEqual(intent.classify("best seo tools")["intent"], "commercial")

    def test_intent_low_confidence_note(self):
        r = intent.classify("公众号排版器")
        self.assertTrue(r["note"])

    def test_auth_link_rejects_phishing(self):
        self.assertFalse(scoring._is_auth_link("https://wikipedia.org.evil.com/x"))
        self.assertTrue(scoring._is_auth_link("https://zh.wikipedia.org/wiki/x"))
        self.assertFalse(scoring._is_auth_link("https://spam.com/page.gov-tricks"))
        self.assertTrue(scoring._is_auth_link("https://nih.gov/study"))


if __name__ == "__main__":
    unittest.main()
