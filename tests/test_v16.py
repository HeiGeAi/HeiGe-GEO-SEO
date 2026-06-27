"""v1.6 测试:内容工程 11 要素加权评分(cescore / content_engineering)+ 复审修复回归。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import content_engineering as ce, htmldoc  # noqa: E402


RICH = """<html lang="zh"><head><title>2026 靠谱电动车品牌选购</title></head><body>
<h1>2026 年靠谱电动车品牌怎么选</h1>
<p>摘要:据中国汽车工业协会《2026 纯电报告》显示,纯电车主满意度达到 87.3%。核心结论如下。</p>
<h2>核心结论</h2>
<ul><li>预算 20 万内首选 A 品牌,续航实测 600 公里</li><li>注重智能化选 B 品牌</li></ul>
<h2>常见问题 FAQ</h2>
<p>问:冬天续航打折多少?答:实测低温续航下降约 30%,来源见 https://example.com/test 。</p>
<table><tr><th>品牌</th><th>续航</th></tr><tr><td>A</td><td>600km</td></tr></table>
<p>续航是指电池满电可行驶里程。本测试由中国科学院某团队、有 10 年从业经验的张工程师参与,
采用多源交叉验证。注意:数据存在地域差异,本文更新于 2026-06-01,仅供参考。</p>
<p>适用场景:家用通勤、城际出行等案例均已覆盖。</p>
</body></html>"""

WEAK = """<html><body><div>买车就买好的,我们最好,赶紧来买,优惠多多,
错过不再有,全网最低价,质量杠杠的,服务一流,值得信赖。</div></body></html>"""


class TestContentEngineeringScore(unittest.TestCase):
    def test_structure_keys(self):
        r = ce.score(htmldoc.from_string(RICH))
        self.assertEqual(r["model"], "content-engineering-11")
        self.assertEqual(len(r["elements"]), 11)
        for e in r["elements"]:
            self.assertIn("weight", e)
            self.assertIn("formula", e)
            self.assertIn("low_confidence", e)
            self.assertLessEqual(e["weighted"], e["weight"] + 0.01)

    def test_weights_sum_98(self):
        r = ce.score(htmldoc.from_string(RICH))
        self.assertEqual(sum(e["weight"] for e in r["elements"]), 98)

    def test_score_normalized_0_100(self):
        # 归一化后强内容可超 50,且最高不超过 100
        r = ce.score(htmldoc.from_string(RICH))
        self.assertGreater(r["score"], 50)
        self.assertLessEqual(r["score"], 100.0)

    def test_rich_beats_weak(self):
        rich = ce.score(htmldoc.from_string(RICH))["score"]
        weak = ce.score(htmldoc.from_string(WEAK))["score"]
        self.assertGreater(rich, weak)
        self.assertLess(weak, 40)

    def test_evidence_layer_raw_capped_43(self):
        r = ce.score(htmldoc.from_string(RICH))
        self.assertEqual(r["evidence_layer_max_raw"], 43)
        self.assertLessEqual(r["evidence_layer_raw"], 43.01)
        self.assertGreater(r["evidence_layer_raw"], 10)

    def test_weakest_three_excludes_low_confidence(self):
        r = ce.score(htmldoc.from_string(WEAK))
        self.assertEqual(len(r["weakest"]), 3)
        names = [w["element"] for w in r["weakest"]]
        self.assertNotIn("语义密度/需求匹配", names)  # 低置信不进排序

    def test_semantic_marked_low_confidence(self):
        r = ce.score(htmldoc.from_string(RICH))
        sem = next(e for e in r["elements"] if e["key"] == "semantic")
        self.assertTrue(sem["low_confidence"])

    def test_render_markdown(self):
        md = ce.render(ce.score(htmldoc.from_string(RICH)))
        self.assertIn("内容工程 11 要素加权评分", md)
        self.assertIn("证据引用层", md)


class TestV16ReviewFixes(unittest.TestCase):
    """复审挖出的真问题的回归测试。"""

    def _stat(self, html):
        r = ce.score(htmldoc.from_string(html))
        return next(e["score_0_1"] for e in r["elements"] if e["key"] == "statistics")

    def _cite(self, html):
        r = ce.score(htmldoc.from_string(html))
        return next(e["score_0_1"] for e in r["elements"] if e["key"] == "citability")

    def test_slash_and_cn_dates_not_statistics(self):
        """斜杠/中文日期不再被当统计数字(历史复发坑)。"""
        dates = ("<html><body><p>更新 2026/06/01 发布 2026/06/02 修订 2026/06/03 "
                 "上线于 2026年6月。版本 v2.0。</p></body></html>")
        stats = "<html><body><p>转化率 87 提升 45 占比 30 共 1200 人参与。</p></body></html>"
        self.assertEqual(self._stat(dates), 0.0)
        self.assertGreater(self._stat(stats), 0.0)

    def test_decimal_stat_not_eaten_as_version(self):
        """87.3% 这类小数统计不应被当版本号剔除。"""
        html = "<html><body><p>满意度 87.3%,增长 12.5%,占比 9.8%。</p></body></html>"
        self.assertGreater(self._stat(html), 0.0)

    def test_bare_ju_not_inflate_citability(self):
        """单字'据'不再被 数据/根据/占据 误命中刷高可引用性。"""
        # 满屏'数据/根据/占据'但零出处零外链
        noise = ("<html><body><p>本文有大量数据,数据驱动,数据分析,根据数据,占据高地,"
                 "数据为王,数据说话。</p></body></html>")
        self.assertLessEqual(self._cite(noise), 0.4)  # 无外链无强出处词,封顶 0.4

    def test_citability_needs_real_anchor(self):
        """有外链或强出处词才放开可引用性上限。"""
        anchored = ('<html><body><p>据《行业白皮书》研究,见 https://a.com/x 。'
                    '来源:https://b.com/y 。出处明确。</p></body></html>')
        self.assertGreater(self._cite(anchored), 0.4)

    def test_evidence_layer_not_maxed_by_garbage(self):
        """纯噪声文本不能把最重的证据层(43)刷满。"""
        garbage = ("<html><body><p>" + "更新 2026/06/01 数据 根据 数据 占据 数据。" * 30
                   + "</p></body></html>")
        r = ce.score(htmldoc.from_string(garbage))
        self.assertLess(r["evidence_layer_raw"], 22)  # 远低于 43

    def test_empty_doc_total_zero(self):
        """空文档总分应为 0(不再靠段落均衡兜底白拿 fluency)。"""
        r = ce.score(htmldoc.from_string(""))
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(len(r["elements"]), 11)

    def test_robustness_date_needs_update_context(self):
        """robustness 的更新日期信号要靠近更新语义,不是随口一个年月就点亮。"""
        def rob(html):
            r = ce.score(htmldoc.from_string(html))
            return next(e["score_0_1"] for e in r["elements"] if e["key"] == "robustness")
        casual = "<html><body><p>那是 2008年8月 的北京奥运会很精彩。</p></body></html>"
        updated = "<html><body><p>本文最后更新于 2026-06-01,内容持续维护。</p></body></html>"
        self.assertGreater(rob(updated), rob(casual))

    def test_semantic_en_stopwords_filtered(self):
        """英文缩写/虚词不应把语义密度刷高。"""
        def sem(html):
            r = ce.score(htmldoc.from_string(html))
            return next(e["score_0_1"] for e in r["elements"] if e["key"] == "semantic")
        junk = "<html><body><p>FAQ HTTP CTO API GPT SDK JSON ROI KPI The Our.</p></body></html>"
        self.assertLess(sem(junk), 0.6)


class TestCescoreCli(unittest.TestCase):
    def test_cli_runs(self):
        import io
        import json
        from contextlib import redirect_stdout
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
        import geo_cli
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "_ce_tmp.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(RICH)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = geo_cli.main(["cescore", "--input", path, "--json"])
            data = json.loads(buf.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(data["model"], "content-engineering-11")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
