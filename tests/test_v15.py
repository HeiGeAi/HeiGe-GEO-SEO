"""v1.5 测试:引用质量层 + agentic/AEO 完善 + SEO 深水区。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import (sov, factcheck, lostprompt, cannibalize, internal_links,  # noqa: E402
                 cwv, token_budget, agent_readiness, scoring, generators, htmldoc)


class TestSovQuality(unittest.TestCase):
    def test_sentiment(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "强烈推荐 Acme"},
                {"prompt": "q2", "engine": "e", "answer": "Acme 有争议不推荐"}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["mention_sentiment"]["positive"]["count"], 1)
        self.assertEqual(r["mention_sentiment"]["negative"]["count"], 1)

    def test_earned_owned_split(self):
        recs = [{"prompt": "q", "engine": "e",
                 "answer": "见 https://acme.com/a 和 https://reddit.com/b 和 https://g2.com/c"}]
        r = sov.analyze(recs, "Acme", brand_domain="acme.com")
        self.assertEqual(r["citation_owned_earned"]["owned"], 1)
        self.assertEqual(r["citation_owned_earned"]["earned"], 2)

    def test_by_turn(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "Acme", "turn": 1},
                {"prompt": "q", "engine": "e", "answer": "没提", "turn": 2}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["by_turn"]["1"]["rate"], 100.0)
        self.assertEqual(r["by_turn"]["2"]["rate"], 0.0)

    def test_no_turn_field_none(self):
        r = sov.analyze([{"prompt": "q", "engine": "e", "answer": "Acme"}], "Acme")
        self.assertIsNone(r["by_turn"])


class TestFactcheck(unittest.TestCase):
    def test_detects_wrong_info(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "智能排版器已停产"}]
        facts = [{"attribute": "状态", "truth": "正常运营", "wrong": ["停产"]}]
        r = factcheck.check(recs, "智能排版器", facts)
        self.assertEqual(r["conflict_count"], 1)
        self.assertEqual(r["conflicts"][0]["truth"], "正常运营")

    def test_no_conflict_when_clean(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "智能排版器很好用"}]
        facts = [{"attribute": "状态", "truth": "正常运营", "wrong": ["停产"]}]
        r = factcheck.check(recs, "智能排版器", facts)
        self.assertEqual(r["conflict_count"], 0)

    def test_skips_answers_without_brand(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "别的产品停产了"}]
        facts = [{"attribute": "状态", "truth": "正常运营", "wrong": ["停产"]}]
        r = factcheck.check(recs, "智能排版器", facts)
        self.assertEqual(r["conflict_count"], 0)


class TestLostprompt(unittest.TestCase):
    def test_identifies_lost(self):
        recs = [{"prompt": "p1", "engine": "e", "answer": "推荐壹伴"},
                {"prompt": "p2", "engine": "e", "answer": "用智能排版器"}]
        r = lostprompt.analyze(recs, "智能排版器", ["壹伴"])
        self.assertEqual(r["lost_count"], 1)
        self.assertEqual(r["won_count"], 1)
        self.assertEqual(r["lost_prompts"][0]["prompt"], "p1")


class TestCannibalize(unittest.TestCase):
    def test_identical_titles_conflict(self):
        pages = [("a.html", "<title>最好的工具</title><h1>最好的工具</h1>"),
                 ("b.html", "<title>最好的工具</title><h1>最好的工具</h1>")]
        r = cannibalize.analyze(pages)
        self.assertEqual(r["conflict_count"], 1)

    def test_distinct_no_conflict(self):
        pages = [("a.html", "<title>苹果价格</title><h1>苹果多少钱</h1>"),
                 ("b.html", "<title>香蕉营养</title><h1>香蕉好处</h1>")]
        r = cannibalize.analyze(pages)
        self.assertEqual(r["conflict_count"], 0)


class TestInternalLinks(unittest.TestCase):
    def test_orphan_detection(self):
        pages = [("/", '<a href="/about">关于</a>'),
                 ("/about", '<a href="/">首页</a>'),
                 ("/orphan", '<p>没人链我</p>')]
        r = internal_links.analyze(pages)
        self.assertIn("/orphan", r["orphan_pages"])
        self.assertNotIn("/about", r["orphan_pages"])

    def test_home_not_orphan(self):
        pages = [("/", '<a href="/a">x</a>'), ("/a", '<p>x</p>')]
        r = internal_links.analyze(pages)
        self.assertNotIn("/", r["orphan_pages"])


class TestCwv(unittest.TestCase):
    def test_good(self):
        r = cwv.assess({"lcp": 2.0, "inp": 100, "cls": 0.05})
        self.assertEqual(r["overall"], "good")

    def test_poor(self):
        r = cwv.assess({"lcp": 5.0, "inp": 100, "cls": 0.05})
        self.assertEqual(r["overall"], "poor")

    def test_missing_unknown(self):
        r = cwv.assess({"lcp": 2.0})
        self.assertEqual(r["metrics"]["inp"]["rating"], "unknown")


class TestToken(unittest.TestCase):
    def test_estimate_nonzero(self):
        self.assertGreater(token_budget.estimate("这是中文 with english 123"), 0)

    def test_over_budget(self):
        r = token_budget.check("一二三四五六七八九十", 3)
        self.assertFalse(r["within_budget"])
        self.assertGreater(r["over_by"], 0)


class TestAgentAntipatterns(unittest.TestCase):
    def test_detects_captcha_file_wall(self):
        doc = htmldoc.from_string(
            '<form><input type=file><div class=g-recaptcha></div></form>必须先注册')
        r = agent_readiness.audit(doc)
        pats = [p["pattern"] for p in r["antipatterns"]]
        self.assertTrue(any("CAPTCHA" in p for p in pats))
        self.assertIn("file 上传输入", pats)
        self.assertIn("强制注册墙", pats)

    def test_imperative_detected(self):
        doc = htmldoc.from_string("<script>navigator.modelContext.registerTool({})</script>")
        r = agent_readiness.audit(doc)
        self.assertTrue(r["imperative_detected"])


class TestScoringReports(unittest.TestCase):
    def test_multimodal_in_result(self):
        r = scoring.score_document(htmldoc.from_string("<h1>x</h1><img src=a><p>字幕</p>"))
        self.assertIn("multimodal", r)
        self.assertTrue(r["multimodal"]["has_transcript_or_captions"])

    def test_onpage_in_result(self):
        r = scoring.score_document(htmldoc.from_string("<title>x</title><h1>t</h1>"))
        self.assertIn("onpage_serp", r)
        self.assertGreater(len(r["onpage_serp"]["tips"]), 0)  # 缺 description/canonical


class TestNewSchemas15(unittest.TestCase):
    def test_action(self):
        node = generators.gen_action("order", "https://x.com/buy?id={id}", name="下单")
        self.assertEqual(node["potentialAction"]["@type"], "OrderAction")
        self.assertEqual(node["potentialAction"]["target"]["@type"], "EntryPoint")

    def test_speakable(self):
        node = generators.gen_speakable([".answer", "h1"])
        self.assertEqual(node["speakable"]["@type"], "SpeakableSpecification")

    def test_software(self):
        node = generators.gen_software_application("X", price=39, rating=4.8)
        self.assertEqual(node["@type"], "SoftwareApplication")
        self.assertEqual(node["offers"]["price"], "39")

    def test_llms_full(self):
        out = generators.gen_llms_full("站名", "简介",
                                       [("页1", "正文1"), {"title": "页2", "body": "正文2"}])
        self.assertIn("## 页1", out)
        self.assertIn("正文2", out)


class TestV15ReviewFixes(unittest.TestCase):
    """四专家复审挖出的问题的回归测试。"""

    def test_sentiment_negation(self):
        for txt in ["Acme 不值得买", "Acme 不好用", "Acme 算不上优秀", "Acme 不可靠"]:
            self.assertEqual(
                sov.parse_answer(txt, ["Acme"])["sentiment"]["Acme"], "negative", txt)

    def test_sentiment_cross_brand_window(self):
        s = sov.parse_answer("首选 Acme,相比之下 Foo 很差不推荐有问题", ["Acme", "Foo"])["sentiment"]
        self.assertEqual(s["Acme"], "positive")
        self.assertEqual(s["Foo"], "negative")

    def test_owned_rejects_phishing_domain(self):
        recs = [{"prompt": "q", "engine": "e",
                 "answer": "见 https://acme.com.evil.com/x 和 https://acme.com/y"}]
        r = sov.analyze(recs, "Acme", brand_domain="acme.com")
        self.assertEqual(r["citation_owned_earned"]["owned"], 1)

    def test_turn_retention(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "Acme", "turn": 1},
                {"prompt": "q", "engine": "e", "answer": "没提了", "turn": 2}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["turn_retention"]["retention_rate"], 0.0)
        recs2 = [{"prompt": "q", "engine": "e", "answer": "Acme", "turn": 1},
                 {"prompt": "q", "engine": "e", "answer": "还是 Acme", "turn": 2}]
        self.assertEqual(sov.analyze(recs2, "Acme")["turn_retention"]["retention_rate"], 100.0)

    def test_internal_links_host_not_eaten(self):
        pages = [("/", '<a href="https://wow.com/a">x</a>'), ("/a", "<p>x</p>")]
        r = internal_links.analyze(pages, base_hosts=["wow.com"])
        self.assertNotIn("/a", r["orphan_pages"])

    def test_factcheck_window_no_misattribution(self):
        recs = [{"prompt": "q", "engine": "e",
                 "answer": "智能排版器很好用。" + "中间内容" * 30 + "那个老竞品已经停产了"}]
        facts = [{"attribute": "状态", "truth": "正常", "wrong": ["停产"]}]
        r = factcheck.check(recs, "智能排版器", facts)
        self.assertEqual(r["conflict_count"], 0)

    def test_factcheck_near_still_flags(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "智能排版器已经停产了"}]
        facts = [{"attribute": "状态", "truth": "正常", "wrong": ["停产"]}]
        r = factcheck.check(recs, "智能排版器", facts)
        self.assertEqual(r["conflict_count"], 1)

    def test_antipattern_cn_captcha(self):
        for html in ["<div class=geetest_panel></div>", "<div>易盾</div>", "<div>防水墙</div>"]:
            r = agent_readiness.audit(htmldoc.from_string(html))
            self.assertTrue(any("CAPTCHA" in p["pattern"] for p in r["antipatterns"]), html)

    def test_sov_missing_prompt_no_crash(self):
        sov.analyze([{"engine": "e", "answer": "Acme"}], "Acme")  # 无 prompt 字段不崩
        lostprompt.analyze([{"engine": "e", "answer": "x"}], "Acme", ["B"])


if __name__ == "__main__":
    unittest.main()
