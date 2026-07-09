"""系统性硬化(v1.11.1)回归测试:审查抽样漏掉的同根实例。

审查暴露两条系统性根因(\\b 词边界在中英交界失效、生成器转义缺失),
审查是抽样的(每维度只深验前 N 条),本文件覆盖主控全库扫出的残余同根实例。
"""
import os
import sys
import unittest
import xml.dom.minidom as minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, content_engineering as ce, generators as g  # noqa: E402


class TestVersionRegexCJK(unittest.TestCase):
    """版本号剥除的 \\b 在汉字紧贴数字处失效(同 F4/intent 根因)。"""

    def _stat(self, html):
        return next(e["score_0_1"] for e in ce.score(htmldoc.from_string(html))["elements"]
                    if e["key"] == "statistics")

    def test_number_count_strips_cjk_adjacent_version(self):
        self.assertEqual(htmldoc.from_string("<p>升级到版本1.2.3后翻倍。</p>").number_count(), 0)

    def test_number_count_strips_space_adjacent_version(self):
        self.assertEqual(htmldoc.from_string("<p>见 1.2.3 版本</p>").number_count(), 0)

    def test_number_count_keeps_two_segment_decimal(self):
        # 87.3 是小数统计,不是版本号,不该被剥
        self.assertEqual(htmldoc.from_string("<p>满意度87.3%,增长12.5%</p>").number_count(), 2)

    def test_number_count_strips_cn_date(self):
        self.assertEqual(htmldoc.from_string("<p>本文更新于2026年6月发布</p>").number_count(), 0)

    def test_statistics_ignores_cjk_adjacent_version(self):
        self.assertLess(self._stat("<p>本工具版本v2.0.1稳定运行,持续维护。</p>"), 0.5)

    def test_statistics_counts_real_numbers(self):
        self.assertGreater(self._stat("<p>转化率提升87%,占比45%,共1200人参与。</p>"), 0)


class TestGeneratorEscaping(unittest.TestCase):
    """[34] 修了 sitemap/feed,hreflang 和 to_script 的转义是审查漏网的同根实例。"""

    def test_hreflang_escapes_ampersand(self):
        frag = g.gen_hreflang([("zh-CN", "https://x.com/p?a=1&b=2")],
                              x_default="https://x.com?c=1&d=2")
        self.assertIn("&amp;", frag)
        self.assertNotIn("?a=1&b=2", frag)
        # 包一个根后应是合法 XML
        minidom.parseString("<head>" + frag + "</head>")

    def test_to_script_escapes_closing_script(self):
        # JSON-LD 内嵌 <script>,答案含 </script> 不转义会提前闭合标签(XSS)
        h = g.to_script(g.gen_faqpage([("q", "</script><script>alert(1)</script>")]))
        self.assertNotIn("</script><script>alert", h)
        self.assertIn("\\u003c", h)
        self.assertEqual(h.count("</script>"), 1)  # 只有结尾那一个真闭合标签

    def test_to_script_json_still_parseable(self):
        import json
        node = g.gen_faqpage([("q<x>", "答案含 <b>标签</b> 和 & 符号")])
        h = g.to_script(node)
        inner = h.split(">\n", 1)[1].rsplit("\n</script>", 1)[0]
        d = json.loads(inner)  # 转义后浏览器 JSON 解析仍无损还原
        self.assertEqual(d["mainEntity"][0]["name"], "q<x>")


if __name__ == "__main__":
    unittest.main()
