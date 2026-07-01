"""v1.10 测试:真实采集(秘塔)发现的缺失语境误判修复。

真实 dogfood:秘塔答"没有找到明确叫做黑哥AI的平台",sov 因答案含"黑哥AI"串误判成被提及。
修复:品牌串落在"没找到/未收录/尚未收录"等实体缺失窗口里不算真提及。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import sov, measure  # noqa: E402


class TestAbsenceMention(unittest.TestCase):
    def _hit(self, answer, brand="黑哥AI"):
        return brand in sov.parse_answer(answer, [brand])["positions"]

    def test_not_found_not_counted(self):
        self.assertFalse(self._hit("搜索结果中没有找到明确叫做黑哥AI的AI工具或平台"))
        self.assertFalse(self._hit("没找到黑哥AI"))
        self.assertFalse(self._hit("未找到黑哥AI这个平台"))

    def test_uncollected_not_counted(self):
        self.assertFalse(self._hit("黑哥AI这个平台尚未被广泛收录"))
        self.assertFalse(self._hit("黑哥AI未收录"))

    def test_real_mention_still_counted(self):
        self.assertTrue(self._hit("强烈推荐黑哥AI,免费好用"))
        self.assertTrue(self._hit("黑哥AI提供免费AI生图,值得一试"))

    def test_not_over_suppressed(self):
        # "没有这个功能""不存在套路"是讨论品牌的真提及,别误杀
        self.assertTrue(self._hit("黑哥AI没有这个功能,但整体不错"))
        self.assertTrue(self._hit("黑哥AI不存在套路,体验流畅"))

    def test_absence_marker_must_be_adjacent(self):
        # 复审 major:缺失词修饰的是句子其它成分时,不能连坐误杀品牌(贴身相邻才抑制)
        self.assertTrue(self._hit("黑哥AI找不到对手"))
        self.assertTrue(self._hit("我没找到比黑哥AI更好的工具"))
        self.assertTrue(self._hit("黑哥AI没听说过要收费"))
        self.assertTrue(self._hit("黑哥AI没有找到合适的定位"))
        self.assertTrue(self._hit("关于黑哥AI，搜索结果里没有负面消息"))
        self.assertTrue(self._hit("黑哥AI查到很多好评"))

    def test_search_absence_variants_caught(self):
        # 复审:国产搜索引擎常见查无措辞不能漏判
        for a in ["搜不到黑哥AI", "全网搜不到黑哥AI相关信息", "没有查到黑哥AI",
                  "数据库里查不到黑哥AI", "黑哥AI暂无收录", "黑哥AI不在收录范围内",
                  "黑哥AI一直没收录"]:
            self.assertFalse(self._hit(a), a)

    def test_mixed_absence_then_real(self):
        # 同一答案先说没找到、后又真推荐(取首个真实出现)
        self.assertTrue(self._hit("没有找到黑哥AI。补充:其实黑哥AI是个不错的免费工具"))

    def test_measure_zero_when_only_absence(self):
        records = [
            {"prompt": "免费AI生图工具哪个好", "engine": "秘塔",
             "answer": "推荐 Stable Diffusion、豆包、即梦。"},
            {"prompt": "黑哥AI是什么", "engine": "秘塔",
             "answer": "搜索结果中没有找到明确叫做黑哥AI的平台,建议您可能记错了名称。"},
        ]
        m = measure.measure_all(records, "黑哥AI")
        self.assertEqual(m["sov"]["coverage"]["rate"], 0.0)  # 真实可见度 0


if __name__ == "__main__":
    unittest.main()
