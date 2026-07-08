"""审查修复回归:sov.py findings [15][16][17][18][19/30][20][39]。

[15] 缺失语境正则被空格击穿(英文/带空格品牌)
[16] "不存在/光杆没有"缺失话术漏判
[17] _URL_RE 吞 URL 后中文/全角标点致 owned 判 earned
[18] 无竞品时 competitive_tier 恒"领导者"
[19/30] turn_retention 按 (prompt,engine) 配对,自然多轮恒 0%
[20] sentiment 裸子串:desktop 命中 top/英文否定不翻转/"没问题"记负面
[39] "找不到X更好的替代品"最高级夸奖被缺失语境误杀
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import sov  # noqa: E402


def _hit(answer, brand="黑哥AI"):
    return brand in sov.parse_answer(answer, [brand])["positions"]


class TestAbsenceWhitespace(unittest.TestCase):
    """[15] 缺失标记与品牌之间的空白不能击穿抑制。"""

    def test_spaced_english_brand_suppressed(self):
        for a in ["找不到 HeiGeAI", "没有找到名为 HeiGeAI 的工具",
                  "HeiGeAI 未被收录", "HeiGeAI 尚未被主流引擎收录",
                  "搜不到 HeiGeAI 相关信息"]:
            self.assertFalse(_hit(a, "HeiGeAI"), a)

    def test_unspaced_still_suppressed(self):
        self.assertFalse(_hit("找不到HeiGeAI", "HeiGeAI"))

    def test_spaced_real_mention_kept(self):
        self.assertTrue(_hit("强烈推荐 HeiGeAI,免费好用", "HeiGeAI"))


class TestAbsenceNotExist(unittest.TestCase):
    """[16] "不存在/光杆没有"缺失话术要抑制,但别误杀真提及。"""

    def test_not_exist_suppressed(self):
        for a in ["不存在叫黑哥AI的产品", "目前没有黑哥AI这个产品",
                  "市面上并没有黑哥AI这款工具", "黑哥AI这个产品不存在",
                  "并不存在黑哥AI"]:
            self.assertFalse(_hit(a), a)

    def test_not_exist_variants_not_over_suppressed(self):
        # v1.10 守的真提及句式在新词表下仍要活着
        self.assertTrue(_hit("黑哥AI不存在套路,体验流畅"))
        self.assertTrue(_hit("黑哥AI没有这个功能,但整体不错"))
        self.assertTrue(_hit("我没找到比黑哥AI更好的工具"))
        # "有没有"是提问不是断言缺失
        self.assertTrue(_hit("不知道有没有黑哥AI这种工具的朋友可以试试"))

    def test_mixed_absence_then_real_counted(self):
        self.assertTrue(_hit("目前没有黑哥AI这个产品的说法不对。其实黑哥AI很好用"))


class TestUrlHostBoundary(unittest.TestCase):
    """[17] URL 后紧跟中文/全角标点/端口不能吞进 host。"""

    def test_cjk_after_url_not_eaten(self):
        p = sov.parse_answer("推荐访问https://heigeai.com了解更多信息。", ["黑哥AI"])
        self.assertIn("heigeai.com", p["citations"])

    def test_fullwidth_paren_and_port(self):
        p = sov.parse_answer("参考（https://heigeai.com）官网和 https://docs.heigeai.com:8443/x", ["黑哥AI"])
        self.assertEqual(p["citations"], ["heigeai.com", "docs.heigeai.com"])

    def test_trailing_ascii_dot_stripped(self):
        p = sov.parse_answer("见 https://heigeai.com.", ["黑哥AI"])
        self.assertEqual(p["citations"], ["heigeai.com"])

    def test_owned_attribution_with_cjk_tail(self):
        r = sov.analyze([{"prompt": "P", "engine": "E",
                          "answer": "推荐访问https://heigeai.com了解更多信息。"}],
                        "黑哥AI", brand_domain="heigeai.com")
        self.assertEqual(r["citation_owned_earned"]["owned"], 1)
        self.assertEqual(r["citation_owned_earned"]["earned"], 0)


class TestTierNoCompetitor(unittest.TestCase):
    """[18] 无竞品时 mention_sov 恒 100%,不能评出"领导者"假档位。"""

    def test_single_brand_low_coverage_not_leader(self):
        recs = [{"prompt": "P%d" % i, "engine": "E", "answer": "推荐一些别的工具"}
                for i in range(9)]
        recs.append({"prompt": "P9", "engine": "E", "answer": "也可以看看黑哥AI"})
        r = sov.analyze(recs, "黑哥AI")
        self.assertEqual(r["competitive_tier"], "无竞品数据,不评档")

    def test_with_competitor_still_classified(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "推荐黑哥AI和竞品B"}]
        r = sov.analyze(recs, "黑哥AI", competitors=["竞品B"])
        self.assertIn(r["competitive_tier"], [t[0] for t in sov._TIERS])


class TestTurnRetentionPairing(unittest.TestCase):
    """[19/30] 多轮对话每轮问句不同,配对不能靠 prompt 文本。"""

    def test_natural_multiturn_retained(self):
        recs = [{"prompt": "排版工具哪个好", "engine": "豆包", "turn": 1, "answer": "推荐黑哥AI"},
                {"prompt": "它比竞品B好在哪", "engine": "豆包", "turn": 2, "answer": "黑哥AI在排版上更强"}]
        r = sov.analyze(recs, "黑哥AI", competitors=["竞品B"])
        self.assertEqual(r["turn_retention"]["first_turn_present"], 1)
        self.assertEqual(r["turn_retention"]["retained_later"], 1)
        self.assertEqual(r["turn_retention"]["retention_rate"], 100.0)

    def test_turn_reset_starts_new_conversation(self):
        recs = [{"prompt": "a", "engine": "e", "turn": 1, "answer": "Acme"},
                {"prompt": "b", "engine": "e", "turn": 2, "answer": "还是 Acme"},
                {"prompt": "c", "engine": "e", "turn": 1, "answer": "Acme"},
                {"prompt": "d", "engine": "e", "turn": 2, "answer": "没提"}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["turn_retention"]["first_turn_present"], 2)
        self.assertEqual(r["turn_retention"]["retained_later"], 1)
        self.assertEqual(r["turn_retention"]["retention_rate"], 50.0)

    def test_orphan_later_turn_not_counted_as_first(self):
        # 只有 turn=2 的孤条不该被当"首轮命中"进分母
        r = sov.analyze([{"prompt": "追问", "engine": "e", "turn": 2, "answer": "Acme"}], "Acme")
        self.assertEqual(r["turn_retention"]["first_turn_present"], 0)
        self.assertIsNone(r["turn_retention"]["retention_rate"])

    def test_explicit_conversation_field_grouping(self):
        recs = [{"prompt": "a", "engine": "e", "turn": 1, "conversation": "c1", "answer": "Acme"},
                {"prompt": "b", "engine": "e", "turn": 2, "conversation": "c1", "answer": "没提"},
                {"prompt": "a", "engine": "e", "turn": 1, "conversation": "c2", "answer": "Acme"},
                {"prompt": "b", "engine": "e", "turn": 2, "conversation": "c2", "answer": "还是 Acme"}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["turn_retention"]["first_turn_present"], 2)
        self.assertEqual(r["turn_retention"]["retention_rate"], 50.0)

    def test_repeated_sample_hit_not_overwritten(self):
        # 同一对话同一轮重复采样,任一次命中即算命中
        recs = [{"prompt": "a", "engine": "e", "turn": 1, "conversation": "c1", "answer": "没提"},
                {"prompt": "a", "engine": "e", "turn": 1, "conversation": "c1", "answer": "Acme"},
                {"prompt": "b", "engine": "e", "turn": 2, "conversation": "c1", "answer": "Acme"}]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(r["turn_retention"]["first_turn_present"], 1)
        self.assertEqual(r["turn_retention"]["retention_rate"], 100.0)


class TestSentimentBoundaries(unittest.TestCase):
    """[20] 情感词典:ASCII 边界、英文否定翻转、"没问题"习语白名单。"""

    def _sent(self, answer, brand="黑哥AI"):
        return sov.parse_answer(answer, [brand])["sentiment"][brand]

    def test_desktop_does_not_hit_top(self):
        self.assertEqual(self._sent("黑哥AI的desktop客户端一般"), "neutral")

    def test_english_negation_flips(self):
        self.assertEqual(self._sent("I would not recommend 黑哥AI at all"), "negative")
        self.assertEqual(self._sent("黑哥AI is not the best option"), "negative")

    def test_meiwenti_idiom_is_praise(self):
        self.assertEqual(self._sent("黑哥AI用起来没问题"), "positive")
        self.assertEqual(self._sent("黑哥AI没有风险,放心用"), "positive")

    def test_real_problem_still_negative(self):
        self.assertEqual(self._sent("黑哥AI出了不少问题"), "negative")

    def test_ascii_word_with_boundary_still_hits(self):
        self.assertEqual(self._sent("黑哥AI is the top choice"), "positive")
        # 词形变化仍命中
        self.assertEqual(self._sent("黑哥AI is highly recommended"), "positive")

    def test_chinese_negation_still_flips(self):
        self.assertEqual(self._sent("黑哥AI不推荐使用"), "negative")


class TestSuperlativePraiseNotSuppressed(unittest.TestCase):
    """[39] "找不到X更好的/X的缺点"是最高级夸奖,不算品牌缺席。"""

    def test_comparative_after_brand_kept(self):
        self.assertTrue(_hit("找不到黑哥AI更好的替代品"))
        self.assertTrue(_hit("我找不到黑哥AI的缺点"))
        self.assertTrue(_hit("搜不到黑哥AI的对手"))

    def test_plain_absence_still_suppressed(self):
        self.assertFalse(_hit("找不到黑哥AI"))
        self.assertFalse(_hit("找不到黑哥AI这个平台"))


if __name__ == "__main__":
    unittest.main()
