"""全项目审查(v1.10.1)核心层修复的回归测试:htmldoc 解析 + scoring robots/F4。"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, scoring  # noqa: E402


class TestSentenceSplit(unittest.TestCase):
    """[3][9] 小数点/域名不拆句,假句子曾扭曲 D1/D3/E4。"""

    def test_decimal_not_split(self):
        d = htmldoc.from_string("<p>提升了3.5倍,成本降低2.8倍。</p>")
        self.assertEqual(len(d.sentences()), 1)

    def test_domain_not_split(self):
        d = htmldoc.from_string("<p>详情访问 heigeai.com 查看报告。</p>")
        self.assertEqual(len(d.sentences()), 1)

    def test_english_sentence_still_splits(self):
        d = htmldoc.from_string("<p>First sentence. Second sentence.</p>")
        self.assertEqual(len(d.sentences()), 2)


class TestSvgTitle(unittest.TestCase):
    """[5] 内联 SVG 的 title 不污染文档标题。"""

    def test_svg_title_excluded(self):
        d = htmldoc.from_string(
            "<html><head><title>黑哥AI首页</title></head><body>"
            "<svg><title>菜单图标</title></svg><svg><title>搜索图标</title></svg>"
            "<h1>正文</h1></body></html>")
        self.assertEqual(d.title, "黑哥AI首页")

    def test_first_title_only(self):
        d = htmldoc.from_string("<title>真标题</title><title>假标题</title>")
        self.assertEqual(d.title, "真标题")


class TestEncodingDetect(unittest.TestCase):
    """[36] GBK 中文页不再被静默读成乱码。"""

    def test_gbk_file(self):
        import tempfile
        html = ('<html lang="zh"><head><meta charset="gbk"><title>国产软件评测</title>'
                "</head><body><h1>企业级AI工具评测</h1><p>本文介绍选型方法。</p></body></html>")
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(html.encode("gbk"))
            path = f.name
        try:
            d = htmldoc.from_file(path)
            self.assertEqual(d.title, "国产软件评测")
            self.assertTrue(d.is_cjk)
        finally:
            os.remove(path)

    def test_utf8_bom_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("﻿User-agent: *\nAllow: /\n".encode("utf-8"))
            path = f.name
        try:
            self.assertTrue(htmldoc.read_text(path).startswith("User-agent"))
        finally:
            os.remove(path)


class TestRobotsParsing(unittest.TestCase):
    """[0] Crawl-delay 结组 / [1] BOM。"""

    def test_crawl_delay_ends_group(self):
        r = scoring.parse_robots(
            "User-agent: bingbot\nCrawl-delay: 5\n\nUser-agent: GPTBot\nDisallow: /\n")
        self.assertEqual(r["groups"]["bingbot"], {"disallow": [], "allow": []})
        self.assertIn("/", r["groups"]["gptbot"]["disallow"])

    def test_bom_stripped(self):
        r = scoring.parse_robots("﻿User-agent: GPTBot\nDisallow: /\n")
        self.assertIn("gptbot", r["groups"])
        self.assertEqual(r["groups"].get("*", {"disallow": []})["disallow"], [])


class TestFreshness(unittest.TestCase):
    """[2][29] F4 新鲜度:旧日期不得满分,中文年份要认。"""

    def _f4(self, html):
        r = scoring.score_document(htmldoc.from_string(html))
        return [c for d in r["dimensions"] for c in d["checks"] if c["id"] == "F4"][0]["earned"]

    def test_stale_time_tag_not_full(self):
        self.assertEqual(self._f4(
            '<h1>旧文</h1><p>老文章。</p><time datetime="2018-01-01">2018</time>'), 0.0)

    def test_recent_time_tag_full(self):
        y = datetime.date.today().year
        self.assertEqual(self._f4(
            '<h1>新文</h1><p>内容。</p><time datetime="%d-01-01">今年</time>' % y), 3.0)

    def test_chinese_year_recognized(self):
        y = datetime.date.today().year
        self.assertGreater(self._f4("<h1>新文</h1><p>本文更新于%d年6月。</p>" % y), 0.0)


if __name__ == "__main__":
    unittest.main()
