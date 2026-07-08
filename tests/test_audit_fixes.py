"""全项目功能审查(v1.10.1)确认问题的回归测试。

审查方式:31 命令真实数据冒烟 + 7 模块群多专家实跑审查 + 对抗验证。
本文件覆盖第一批确认的 8 条(sourcing/recommend/intent 模块群)。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import platform_recommend as pr, sourcing, intent  # noqa: E402


class TestReverseFixes(unittest.TestCase):
    """#1 大小写 / #5 CONTENT_TYPE 覆盖 / #6 子串误命中。"""

    def test_lowercase_english_platform(self):
        for q in ("reddit", "linkedin", "youtube", "wikipedia"):
            self.assertGreater(pr.reverse(q)["engine_count"], 0, q)

    def test_x_twitter_aliases(self):
        self.assertGreater(pr.reverse("x")["engine_count"], 0)
        self.assertGreater(pr.reverse("twitter")["engine_count"], 0)

    def test_content_type_platforms_reverse(self):
        # 正向 recommend 推荐过的平台,反查不能答 0
        for q in ("小红书", "B站", "CSDN", "G2"):
            self.assertGreater(pr.reverse(q)["engine_count"], 0, q)

    def test_short_ascii_substring_no_false_hit(self):
        self.assertEqual(pr.reverse("in")["engine_count"], 0)
        self.assertEqual(pr.reverse("it")["engine_count"], 0)

    def test_chinese_substring_still_works(self):
        self.assertGreaterEqual(pr.reverse("知乎")["engine_count"], 4)

    def test_no_hit_has_note(self):
        r = pr.reverse("不存在的平台xyz")
        self.assertEqual(r["engine_count"], 0)
        self.assertIn("note", r)

    def test_matched_platform_disclosed(self):
        r = pr.reverse("reddit")
        self.assertIn("Reddit", r["matched_platforms"])


class TestIntentFixes(unittest.TestCase):
    """#2 中英交界词边界 / #8 子串信号重复计数。"""

    def test_cjk_adjacent_english_signal(self):
        self.assertEqual(intent.classify("豆包vs元宝")["intent"], "commercial")
        self.assertEqual(intent.classify("AI工具review")["intent"], "commercial")

    def test_vs_dot_form(self):
        self.assertEqual(intent.classify("A vs. B")["intent"], "commercial")

    def test_word_boundary_still_guards(self):
        # whichever 不应命中 which,reorder 不应命中 order
        self.assertNotIn("which", intent.classify("whichever tool works")["signals_matched"])
        self.assertNotIn("order", intent.classify("reorder the list")["signals_matched"])

    def test_substring_signals_dedup(self):
        r = intent.classify("深度学习怎么样")
        self.assertEqual(r["signals_matched"], ["怎么样"])  # 不再同时记 怎么+怎么样
        self.assertNotEqual(r["confidence"], "high")

    def test_mixed_query_not_flipped_by_double_count(self):
        # "多少钱怎么样":transactional 1 分 vs informational 1 分,并列时交易优先
        self.assertEqual(intent.classify("iPhone 17 多少钱怎么样")["intent"], "transactional")


class TestContentTypeFixes(unittest.TestCase):
    """#3 fallback 灌非目标引擎 / #7 未识别引擎静默。"""

    def test_no_foreign_engines_in_feeds(self):
        r = pr.recommend(["豆包"], content_type="b2b")
        for row in r["recommendations"]:
            for e in row["feeds_engines"]:
                self.assertEqual(e, "豆包", "非目标引擎 %s 混进 feeds(%s)" % (e, row["platform"]))

    def test_relevant_content_type_still_added(self):
        # 豆包+种草:小红书 eng_list 含豆包,应正常追加
        r = pr.recommend(["豆包"], content_type="种草")
        plats = [x["platform"] for x in r["recommendations"]]
        self.assertIn("小红书", plats)

    def test_unknown_engine_surfaced(self):
        r = pr.recommend(["bard"], content_type="b2b")
        self.assertEqual(r["recommendations"], [])
        self.assertEqual(r["unrecognized_engines"], ["bard"])
        self.assertIn("未识别的引擎", pr.render_markdown(r))

    def test_known_engine_no_false_flag(self):
        self.assertIsNone(pr.recommend(["豆包"])["unrecognized_engines"])


class TestLifelineFixes(unittest.TestCase):
    """#4 content_type 加分击穿命脉相对档。"""

    def test_yuanbao_video_lifeline_in_p0(self):
        p = sourcing.plan("x", ["y"], ["元宝"], content_type="video")
        p0 = [t["platform"] for t in p["delivery_sop"]["tiers"]["P0"]]
        self.assertIn("微信公众号", p0)  # 元宝命脉(独家信源)不被视频号+2挤出

    def test_copilot_b2b_lifeline_in_p0(self):
        p = sourcing.plan("x", ["y"], ["copilot"], content_type="b2b")
        p0 = [t["platform"] for t in p["delivery_sop"]["tiers"]["P0"]]
        self.assertIn("官网+Schema", p0)

    def test_all_single_engine_lifelines_p0(self):
        # 每个引擎单独跑:其原生最高权重平台必须都在 P0(模块 docstring 的保证)
        for eng in pr.CN_ENGINES + pr.OVERSEAS_ENGINES:
            plats = pr._ENGINE_PLATFORMS.get(eng, [])
            if not plats:
                continue
            top_w = max(w for _, w, _, _ in plats)
            lifelines = {pl for pl, w, _, _ in plats if w == top_w}
            p = sourcing.plan("x", ["y"], [eng])
            p0 = {t["platform"] for t in p["delivery_sop"]["tiers"]["P0"]}
            self.assertTrue(lifelines <= p0, "%s 命脉 %s 不全在 P0 %s" % (eng, lifelines, p0))

    def test_no_fake_consensus_from_foreign_feeds(self):
        # copilot+b2b:LinkedIn 只剩 copilot 原生权重,不该靠伪造 feeds 进 P0 共识档
        p = sourcing.plan("x", ["y"], ["copilot"], content_type="b2b")
        for tier in ("P0", "P1", "P2"):
            for t in p["delivery_sop"]["tiers"][tier]:
                for e in t["feeds_engines"]:
                    self.assertEqual(e, "copilot")


if __name__ == "__main__":
    unittest.main()
