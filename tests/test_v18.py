"""v1.8 测试:旗舰 playbook 作战手册编排器 + measure 监测采集闭环。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import playbook, measure, htmldoc  # noqa: E402


WEAK = """<html lang="zh"><head><title>排版工具</title></head><body>
<div>买就买好的,我们最好,赶紧来,优惠多多,质量杠杠的。</div></body></html>"""

RICH = """<html lang="zh"><head><title>选购</title></head><body>
<h1>2026靠谱排版工具怎么选,哪个好</h1>
<p>摘要:据《中国行业白皮书》研究显示,90%运营者用工具提效,转化率提升45%。来源 https://a.com 。</p>
<h2>核心结论</h2><ul><li>免费选A,实测3分钟出图,出处 https://b.com</li></ul>
<h2>常见问题FAQ</h2><p>问:多少钱?答:基础版免费。参考研究 https://c.com 。</p>
<table><tr><th>工具</th><th>速度</th></tr><tr><td>A</td><td>3分钟</td></tr></table>
<p>排版是指视觉编排。本测试由中国科学院某团队、有10年从业经验的张工程师参与,多源交叉验证。
注意:有地域差异,本文更新于2026-06-01。适用场景:公众号、新闻稿等案例已覆盖。</p>
</body></html>"""

RECORDS = [
    {"prompt": "公众号排版工具哪个好", "engine": "豆包", "answer": "推荐壹伴和智能排版器,智能排版器免费"},
    {"prompt": "最好的排版工具", "engine": "豆包", "answer": "壹伴不错"},
]


class TestPlaybook(unittest.TestCase):
    def test_structure(self):
        pb = playbook.generate(htmldoc.from_string(WEAK), brand="智能排版器",
                               category="公众号排版工具", engines=["豆包"])
        for k in ("bottleneck", "score_6dim", "content_engineering", "diagnosis",
                  "sourcing", "unified_actions", "measure_kit"):
            self.assertIn(k, pb)

    def test_weak_content_bottleneck_is_content(self):
        pb = playbook.generate(htmldoc.from_string(WEAK), brand="X", category="工具",
                               engines=["豆包"])
        self.assertIn("内容质量层", pb["bottleneck"]["bottleneck_layer"])

    def test_strong_content_global_bottleneck_is_sourcing(self):
        # 内容过关 + 海外市场(无 ICP 收录障碍)→ 瓶颈转到信源策略层
        pb = playbook.generate(htmldoc.from_string(RICH), brand="X", category="tool",
                               engines=["chatgpt"], market="global")
        self.assertGreaterEqual(pb["content_engineering"]["score"], 55)
        self.assertIn("信源策略层", pb["bottleneck"]["bottleneck_layer"])

    def test_unified_actions_sorted(self):
        pb = playbook.generate(htmldoc.from_string(WEAK), brand="X", category="工具",
                               engines=["豆包"])
        prios = [a["prio"] for a in pb["unified_actions"]]
        self.assertEqual(prios, sorted(prios))
        # 证据引用层(prio 1)应排在最前
        self.assertEqual(pb["unified_actions"][0]["layer"], "内容质量")

    def test_render(self):
        md = playbook.render_markdown(playbook.generate(
            htmldoc.from_string(WEAK), brand="智能排版器", category="工具", engines=["豆包"]))
        self.assertIn("GEO 作战手册", md)
        self.assertIn("八层瓶颈定位", md)
        self.assertIn("统一行动清单", md)

    def test_no_brand_no_crash(self):
        pb = playbook.generate(htmldoc.from_string(WEAK), brand=None, category=None,
                               engines=None)
        self.assertIn("bottleneck", pb)


class TestMeasure(unittest.TestCase):
    def test_collection_kit(self):
        from lib import prompts as promptlib
        rows = promptlib.generate("智能排版器", "公众号排版工具", limit=10)
        kit = measure.collection_kit("智能排版器", ["豆包", "元宝"], rows, competitors=["壹伴"])
        self.assertEqual(kit["sample_per_prompt_engine"], 5)
        self.assertTrue(len(kit["prompts_to_ask"]) > 0)
        self.assertIn("records_schema", kit)
        self.assertEqual(len(kit["feed_back"]), 3)

    def test_measure_all_runs_three(self):
        m = measure.measure_all(RECORDS, "智能排版器", competitors=["壹伴"],
                                facts=[{"attribute": "价格", "truth": "免费", "wrong": ["收费"]}])
        self.assertIsNotNone(m["sov"])
        self.assertIsNotNone(m["lostprompt"])
        self.assertIsNotNone(m["factcheck"])
        self.assertEqual(m["record_count"], 2)

    def test_measure_coverage_rate(self):
        m = measure.measure_all(RECORDS, "智能排版器")
        # 智能排版器在 2 个 prompt 中提到 1 次 → 50%
        self.assertEqual(m["sov"]["coverage"]["rate"], 50.0)

    def test_render_measure_shows_rate(self):
        md = measure.render_measure(measure.measure_all(RECORDS, "智能排版器", competitors=["壹伴"]))
        self.assertIn("问句覆盖率", md)
        self.assertIn("竞品夺走", md)

    def test_measure_no_competitor_no_lostprompt(self):
        m = measure.measure_all(RECORDS, "智能排版器")
        self.assertIsNone(m["lostprompt"])
        self.assertIsNone(m["factcheck"])


class TestV18Cli(unittest.TestCase):
    def _run(self, argv):
        import io
        import json
        from contextlib import redirect_stdout
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
        import geo_cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = geo_cli.main(argv)
        return rc, buf.getvalue()

    def test_playbook_cli(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "_pb18.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(WEAK)
        try:
            rc, out = self._run(["playbook", "--input", path, "--brand", "X",
                                 "--category", "工具", "--engine", "豆包", "--json"])
            import json
            self.assertEqual(rc, 0)
            self.assertIn("bottleneck", json.loads(out))
        finally:
            os.remove(path)

    def test_measure_kit_cli(self):
        rc, out = self._run(["measure", "--kit", "--brand", "X", "--category", "工具",
                             "--engine", "豆包", "--json"])
        import json
        self.assertEqual(rc, 0)
        self.assertIn("records_schema", json.loads(out))

    def test_measure_missing_input_exits_2(self):
        rc, _ = self._run(["measure", "--brand", "X"])  # 无 --kit 无 --input
        self.assertEqual(rc, 2)


class TestV18ReviewFixes(unittest.TestCase):
    """v1.8 复审挖出的问题的回归测试。"""

    def test_bottleneck_has_confidence(self):
        pb = playbook.generate(htmldoc.from_string(WEAK), brand="X", category="工具",
                               engines=["豆包"])
        self.assertIn("confidence", pb["bottleneck"])
        self.assertIn("detection_boundary", pb["bottleneck"])

    def test_index_layer_label_honest(self):
        # 索引层文案应标明仅检测 ICP 备案信号
        WEAK_CN = "<html lang='zh'><body><div>没有备案号的弱内容站</div></body></html>"
        pb = playbook.generate(htmldoc.from_string(WEAK_CN), brand="X", category="工具",
                               engines=["豆包"])
        # 内容太弱仍先判内容层;此处只验 detection_boundary 提到 ICP 边界
        self.assertIn("ICP", pb["bottleneck"]["detection_boundary"])

    def test_kit_empty_engines_basis_is_platforms(self):
        kit = measure.collection_kit("X", [], [{"prompt": "q"}])
        self.assertFalse(kit["engines_specified"])
        self.assertEqual(kit["estimate_basis"], 5)  # 未指定引擎按 5 平台估算

    def test_kit_render_no_collected_wording(self):
        from lib import prompts as promptlib
        rows = promptlib.generate("X", "工具", limit=5)
        md = measure.render_kit(measure.collection_kit("X", [], rows))
        self.assertIn("尚未采集", md)  # 待办态,不读成已采

    def test_measure_render_coverage_label(self):
        md = measure.render_measure(measure.measure_all(RECORDS, "智能排版器"))
        self.assertIn("问句覆盖率", md)
        self.assertNotIn("被推荐概率(覆盖率)", md)  # 旧误导标签已去


if __name__ == "__main__":
    unittest.main()
