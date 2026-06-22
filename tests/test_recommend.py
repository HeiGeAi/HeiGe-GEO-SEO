import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import platform_recommend as pr  # noqa: E402


class TestRecommend(unittest.TestCase):
    def test_doubao_recommends_bytedance(self):
        r = pr.recommend(["豆包"])
        plats = [x["platform"] for x in r["recommendations"]]
        self.assertIn("今日头条", plats[:3])
        self.assertIn("抖音", plats[:3])

    def test_yuanbao_recommends_wechat(self):
        r = pr.recommend(["元宝"])
        top = r["recommendations"][0]["platform"]
        self.assertEqual(top, "微信公众号")

    def test_multi_engine_shared_platform_ranks_high(self):
        # 搜狐 feeds both 豆包 and 元宝 -> should aggregate
        r = pr.recommend(["豆包", "元宝"])
        sohu = next(x for x in r["recommendations"] if x["platform"] == "搜狐")
        self.assertEqual(set(sohu["feeds_engines"]), {"豆包", "元宝"})

    def test_alias_resolution(self):
        r1 = pr.recommend(["doubao"])
        r2 = pr.recommend(["豆包"])
        self.assertEqual([x["platform"] for x in r1["recommendations"]],
                         [x["platform"] for x in r2["recommendations"]])

    def test_cn_all_preset(self):
        r = pr.recommend(["cn-all"])
        self.assertEqual(len(r["target_engines"]), 6)

    def test_overseas_recommends_reddit(self):
        r = pr.recommend(["chatgpt", "perplexity"])
        reddit = next(x for x in r["recommendations"] if x["platform"] == "Reddit")
        self.assertGreaterEqual(reddit["score"], 6)

    def test_content_type_video_boost(self):
        r = pr.recommend(["豆包"], content_type="video")
        douyin = next(x for x in r["recommendations"] if x["platform"] == "抖音")
        self.assertGreaterEqual(douyin["score"], 5)

    def test_reverse_lookup(self):
        r = pr.reverse("知乎")
        self.assertGreaterEqual(r["engine_count"], 4)

    def test_render_markdown(self):
        md = pr.render_markdown(pr.recommend(["豆包"]))
        self.assertIn("平台发布推荐", md)
        self.assertIn("新榜", md)

    def test_top_limit(self):
        r = pr.recommend(["cn-all"], top=3)
        self.assertEqual(len(r["recommendations"]), 3)


class TestOverseasV13(unittest.TestCase):
    def test_overseas_all_has_eleven_engines(self):
        r = pr.recommend(["overseas-all"])
        self.assertEqual(len(r["target_engines"]), 11)

    def test_chatgpt_top_is_wikipedia(self):
        r = pr.recommend(["chatgpt"])
        self.assertEqual(r["recommendations"][0]["platform"], "Wikipedia")

    def test_gemini_does_not_recommend_reddit(self):
        # Gemini 几乎不引 Reddit(0.1%),不应出现在推荐里
        r = pr.recommend(["gemini"])
        plats = [x["platform"] for x in r["recommendations"]]
        self.assertNotIn("Reddit", plats)

    def test_perplexity_loves_reddit_and_g2(self):
        r = pr.recommend(["perplexity"])
        plats = [x["platform"] for x in r["recommendations"]]
        self.assertIn("Reddit", plats)
        self.assertIn("G2", plats)

    def test_new_engines_resolve(self):
        for alias, canon in [("copilot", "copilot"), ("bing", "copilot"),
                             ("grok", "grok"), ("meta", "metaai"),
                             ("brave", "brave"), ("lechat", "mistral"),
                             ("ddg", "duckduckgo")]:
            r = pr.recommend([alias])
            self.assertEqual(r["target_engines"], [canon])

    def test_grok_recommends_x(self):
        r = pr.recommend(["grok"])
        self.assertEqual(r["recommendations"][0]["platform"], "X/Twitter")

    def test_b2b_boosts_g2_linkedin(self):
        r = pr.recommend(["chatgpt", "perplexity"], content_type="b2b")
        top2 = [x["platform"] for x in r["recommendations"][:2]]
        self.assertIn("LinkedIn", top2)
        self.assertIn("G2", top2)

    def test_overseas_note_has_volatility_warning(self):
        r = pr.recommend(["chatgpt"])
        self.assertIn("翻盘", r["note"])

    def test_cn_note_no_overseas_warning(self):
        r = pr.recommend(["豆包"])
        self.assertNotIn("翻盘", r["note"])

    def test_reverse_has_region_tag(self):
        r = pr.reverse("Reddit")
        self.assertTrue(all("region" in f for f in r["feeds_engines"]))
        self.assertTrue(any(f["region"] == "海外" for f in r["feeds_engines"]))


if __name__ == "__main__":
    unittest.main()
