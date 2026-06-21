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


if __name__ == "__main__":
    unittest.main()
