"""v1.9 测试:playbook HTML 作战手册渲染 + compare 对标作战。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import playbook, htmldoc  # noqa: E402


STRONG = """<html lang="zh"><head><title>选购</title></head><body>
<h1>2026靠谱排版工具怎么选,哪个好</h1>
<p>摘要:据《中国行业白皮书》研究显示,90%运营者用工具提效,转化率提升45%。来源 https://a.com 。</p>
<h2>核心结论</h2><ul><li>免费选A,实测3分钟出图,出处 https://b.com</li></ul>
<h2>常见问题FAQ</h2><p>问:多少钱?答:基础版免费。参考研究 https://c.com 。</p>
<table><tr><th>工具</th><th>速度</th></tr><tr><td>A</td><td>3分钟</td></tr></table>
<p>排版是指视觉编排。本测试由中国科学院某团队、有10年从业经验的张工程师参与,多源交叉验证。
注意:有地域差异,本文更新于2026-06-01。适用场景:公众号、新闻稿等案例已覆盖。</p>
</body></html>"""

WEAK = """<html lang="zh"><head><title>竞品</title></head><body>
<div>我们的工具最好用,快来买,优惠多。</div></body></html>"""


class TestPlaybookHtml(unittest.TestCase):
    def _html(self):
        pb = playbook.generate(htmldoc.from_string(STRONG), brand="智能排版器",
                               category="公众号排版工具", engines=["豆包", "元宝"],
                               competitors=["壹伴"])
        return playbook.render_html(pb)

    def test_valid_html_structure(self):
        h = self._html()
        self.assertTrue(h.startswith("<!DOCTYPE html>"))
        self.assertIn("八层瓶颈定位", h)
        self.assertIn("统一行动清单", h)
        self.assertIn("信源策略", h)
        self.assertIn("监测采集闭环", h)

    def test_no_script_static(self):
        self.assertNotIn("<script", self._html())  # 静态零动画

    def test_div_balanced(self):
        h = self._html()
        self.assertEqual(h.count("<div"), h.count("</div"))

    def test_print_media(self):
        self.assertIn("@media print", self._html())

    def test_escapes_brand(self):
        pb = playbook.generate(htmldoc.from_string(STRONG), brand="<x>&", category="t",
                               engines=["豆包"])
        h = playbook.render_html(pb)
        self.assertNotIn("<x>&</", h)  # 应被转义
        self.assertIn("&lt;x&gt;", h)


class TestCompare(unittest.TestCase):
    def _pages(self):
        return [("我", htmldoc.from_string(STRONG)), ("竞品", htmldoc.from_string(WEAK))]

    def test_ranks_strong_first(self):
        c = playbook.compare(self._pages())
        self.assertEqual(c["you"], "我")
        ranked = sorted(c["rows"], key=lambda r: r["rank"])
        self.assertEqual(ranked[0]["label"], "我")  # 强内容排第一
        self.assertEqual(c["you_rank"], 1)

    def test_gaps_structure(self):
        c = playbook.compare(self._pages())
        for g in c["gaps"]:
            self.assertIn("element", g)
            self.assertGreater(g["gap"], 0)

    def test_single_page_no_competitor(self):
        c = playbook.compare([("我", htmldoc.from_string(STRONG))])
        self.assertEqual(c["you_rank"], 1)
        self.assertIn("没有竞品", c["verdict"])

    def test_empty(self):
        c = playbook.compare([])
        self.assertIsNone(c["you"])

    def test_render(self):
        md = playbook.render_compare(playbook.compare(self._pages()))
        self.assertIn("对标作战", md)
        self.assertIn("综合分", md)

    def test_losing_page_ranked_lower(self):
        # 弱页放第一位(你),应被判落后
        c = playbook.compare([("我弱", htmldoc.from_string(WEAK)),
                              ("强竞品", htmldoc.from_string(STRONG))])
        self.assertEqual(c["you_rank"], 2)
        self.assertIn("落后", c["verdict"])


class TestV19ReviewFixes(unittest.TestCase):
    """v1.9 复审挖出的问题的回归测试。"""

    def test_gaps_ignore_weaker_competitor_inflated_element(self):
        # 垃圾竞品(综合分低)在 fluency 上虚高,不应被列成你的差距
        c = playbook.compare([("我", htmldoc.from_string(STRONG)),
                              ("垃圾竞品", htmldoc.from_string(WEAK))])
        self.assertEqual(c["you_rank"], 1)
        names = [g["element"] for g in c["gaps"]]
        self.assertNotIn("表达流畅度", names)
        self.assertNotIn("易懂表达", names)

    def test_tie_verdict_says_draw_not_lead(self):
        # 两张相同页打平,不应说"领先"
        c = playbook.compare([("我", htmldoc.from_string(STRONG)),
                              ("克隆", htmldoc.from_string(STRONG))])
        self.assertIn("打平", c["verdict"])
        self.assertNotIn("领先", c["verdict"])

    def test_verdict_has_offline_qualifier(self):
        c = playbook.compare([("我", htmldoc.from_string(STRONG)),
                              ("弱", htmldoc.from_string(WEAK))])
        self.assertIn("内容质量", c["verdict"])  # 不再裸称"综合分"

    def test_html_evidence_label_directional(self):
        pb = playbook.generate(htmldoc.from_string(STRONG), brand="X", category="t",
                               engines=["豆包"])
        h = playbook.render_html(pb)
        self.assertIn("方向性口径", h)  # 第一杠杆加了口径限定
        self.assertNotIn("被引用第一杠杆", h)

    def test_html_single_quote_gone(self):
        pb = playbook.generate(htmldoc.from_string(STRONG), brand="X", category="t",
                               engines=None)  # 空引擎走兜底 div
        h = playbook.render_html(pb)
        self.assertNotIn("style='color", h)  # 单引号属性已统一


class TestV19Cli(unittest.TestCase):
    def _run(self, argv):
        import io
        from contextlib import redirect_stdout
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
        import geo_cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = geo_cli.main(argv)
        return rc, buf.getvalue()

    def test_playbook_html_writes_file(self):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        src = os.path.join(fx, "_pb19.html")
        out = os.path.join(fx, "_pb19_out.html")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(STRONG)
        try:
            rc, _ = self._run(["playbook", "--input", src, "--brand", "X",
                               "--category", "工具", "--engine", "豆包", "--html", out])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as fh:
                self.assertIn("作战手册", fh.read())
        finally:
            for p in (src, out):
                if os.path.exists(p):
                    os.remove(p)

    def test_compare_missing_competitor_exits_2(self):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        mine = os.path.join(fx, "_c19c.html")
        with open(mine, "w", encoding="utf-8") as fh:
            fh.write(STRONG)
        try:
            rc, _ = self._run(["compare", "--input", mine,
                               "--competitor-page", "竞品::/不存在的路径xyz.html"])
            self.assertEqual(rc, 2)
        finally:
            os.remove(mine)

    def test_compare_cli(self):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        mine = os.path.join(fx, "_c19a.html")
        comp = os.path.join(fx, "_c19b.html")
        with open(mine, "w", encoding="utf-8") as fh:
            fh.write(STRONG)
        with open(comp, "w", encoding="utf-8") as fh:
            fh.write(WEAK)
        try:
            rc, out = self._run(["compare", "--input", mine, "--label", "我",
                                 "--competitor-page", "竞品::" + comp, "--json"])
            import json
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["you"], "我")
        finally:
            for p in (mine, comp):
                os.remove(p)


if __name__ == "__main__":
    unittest.main()
