"""审查修复回归测试(misc-auditors 组):
[25] cannibalize 品牌后缀误报 / [28] 中文换序漏检
[26] internal_links 协议相对链接 / [27] 相对链接孤儿误判
[14] factcheck truth 覆盖 wrong 误报
[34] gen_sitemap/gen_feed_xml XML 转义
[45] attribution 解析失败行误当 UA
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import (cannibalize, internal_links, factcheck, generators,  # noqa: E402
                 attribution, htmldoc)


class TestCannibalizeBrandSuffix(unittest.TestCase):
    """[25] 「页名 - 品牌名」统一后缀不该把无关页顶成蚕食。"""

    def test_brand_suffix_no_false_positive(self):
        p1 = "<html><head><title>公司简介 - 黑哥AI实验室</title></head><body><h1>公司简介</h1></body></html>"
        p2 = "<html><head><title>联系方式 - 黑哥AI实验室</title></head><body><h1>联系方式</h1></body></html>"
        r = cannibalize.analyze([("a", p1), ("b", p2)])
        self.assertEqual(r["conflict_count"], 0)

    def test_pipe_separator_suffix(self):
        p1 = "<html><head><title>价格方案 | Acme</title></head><body><h1>价格方案</h1></body></html>"
        p2 = "<html><head><title>关于我们 | Acme</title></head><body><h1>关于我们</h1></body></html>"
        r = cannibalize.analyze([("a", p1), ("b", p2)])
        self.assertEqual(r["conflict_count"], 0)

    def test_same_intent_with_suffix_still_detected(self):
        # 剥掉后缀后真蚕食仍要报
        p1 = "<html><head><title>北京火锅推荐 - 黑哥AI</title></head><body><h1>北京火锅推荐</h1></body></html>"
        p2 = "<html><head><title>北京火锅店推荐榜 - 黑哥AI</title></head><body><h1>北京火锅店推荐榜</h1></body></html>"
        r = cannibalize.analyze([("a", p1), ("b", p2)])
        self.assertEqual(r["conflict_count"], 1)


class TestCannibalizeCjkReorder(unittest.TestCase):
    """[28] 同样的中文词换序不该漏检(滑窗 bigram 词序无关)。"""

    def test_reordered_title_detected(self):
        p1 = "<html><head><title>北京火锅店推荐榜单</title></head><body><h1>北京火锅店推荐榜单</h1></body></html>"
        p2 = "<html><head><title>推荐榜单：北京火锅店</title></head><body><h1>推荐榜单：北京火锅店</h1></body></html>"
        r = cannibalize.analyze([("a", p1), ("b", p2)])
        self.assertEqual(r["conflict_count"], 1)

    def test_distinct_topics_still_clean(self):
        p1 = "<html><head><title>苹果价格走势</title></head><body><h1>苹果多少钱</h1></body></html>"
        p2 = "<html><head><title>香蕉营养分析</title></head><body><h1>香蕉好处</h1></body></html>"
        r = cannibalize.analyze([("a", p1), ("b", p2)])
        self.assertEqual(r["conflict_count"], 0)


class TestInternalLinksProtocolRelative(unittest.TestCase):
    """[26] //host/path 协议相对链接按域名判定,别当站内路径。"""

    def test_protocol_relative_external_rejected(self):
        self.assertIsNone(internal_links._norm("//evil.cdn.com/track", {"mysite.com"}))

    def test_protocol_relative_own_host_accepted(self):
        self.assertEqual(internal_links._norm("//mysite.com/about", {"mysite.com"}), "/about")

    def test_absolute_url_without_base_hosts_not_internal(self):
        # 不传 base_hosts 时带域名的链接无法判定,一律不计(与 note 语义对齐)
        self.assertIsNone(internal_links._norm("https://twitter.com/heige", set()))

    def test_analyze_not_polluted(self):
        pages = [("/", '<a href="//cdn.other.com/lib">x</a><a href="/about">a</a>'),
                 ("/about", "")]
        r = internal_links.analyze(pages, base_hosts=["mysite.com"])
        self.assertEqual(r["internal_links_total"], 1)


class TestInternalLinksRelativeResolution(unittest.TestCase):
    """[27] 全相对链接互链的站点不该 100% 孤儿。"""

    def test_relative_links_resolved(self):
        pages = [("/guide/intro", '<a href="setup">s</a><a href="usage">u</a>'),
                 ("/guide/setup", '<a href="intro">i</a><a href="usage">u</a>'),
                 ("/guide/usage", '<a href="intro">i</a><a href="setup">s</a>')]
        r = internal_links.analyze(pages)
        self.assertEqual(r["orphan_count"], 0)
        self.assertEqual(r["internal_links_total"], 6)
        self.assertEqual(r["verdict"], "内链结构健康")

    def test_dot_and_parent_relative(self):
        pages = [("/docs/a", '<a href="./b">b</a><a href="../top">t</a>'),
                 ("/docs/b", '<a href="a">a</a>'),
                 ("/top", '<a href="/docs/a">a</a>')]
        r = internal_links.analyze(pages, home="/docs/a")
        self.assertEqual(r["orphan_count"], 0)

    def test_non_http_scheme_skipped(self):
        # tel:/mailto:/javascript: 不该被当成相对路径解析
        for href in ["tel:+8612345678", "mailto:a@b.com", "javascript:void(0)"]:
            self.assertIsNone(internal_links._norm(href, set(), base="/page"), href)


class TestFactcheckTruthCoversWrong(unittest.TestCase):
    """[14] wrong 是 truth 子串时,AI 复述真相不算冲突。"""

    def test_truth_superstring_no_conflict(self):
        recs = [{"prompt": "P", "engine": "豆包",
                 "answer": "黑哥AI排版器价格是199元/月,值得买。"}]
        facts = [{"attribute": "价格", "truth": "199元/月", "wrong": ["99元/月"]}]
        r = factcheck.check(recs, "黑哥AI", facts)
        self.assertEqual(r["conflict_count"], 0)

    def test_genuine_wrong_still_flagged(self):
        recs = [{"prompt": "P", "engine": "豆包",
                 "answer": "黑哥AI排版器价格是99元/月。"}]
        facts = [{"attribute": "价格", "truth": "199元/月", "wrong": ["99元/月"]}]
        r = factcheck.check(recs, "黑哥AI", facts)
        self.assertEqual(r["conflict_count"], 1)

    def test_version_prefix_case(self):
        # 版本号 12.0 覆盖 wrong=2.0;另一处独立的 2.0 仍要报
        recs = [{"prompt": "P", "engine": "e", "answer": "Acme 最新版本是 12.0。"}]
        facts = [{"attribute": "版本", "truth": "12.0", "wrong": ["2.0"]}]
        self.assertEqual(factcheck.check(recs, "Acme", facts)["conflict_count"], 0)
        recs2 = [{"prompt": "P", "engine": "e", "answer": "Acme 版本还停在 2.0。"}]
        self.assertEqual(factcheck.check(recs2, "Acme", facts)["conflict_count"], 1)


class TestGeneratorsXmlEscape(unittest.TestCase):
    """[34] sitemap/feed 里的 URL/标题必须做 XML 实体转义。"""

    def test_sitemap_query_params_valid_xml(self):
        xml = generators.gen_sitemap([("https://heigeai.com/page?a=1&b=2", "2026-07-01"),
                                      "https://heigeai.com/plain"])
        ET.fromstring(xml)  # 非法 XML 会抛异常
        self.assertIn("a=1&amp;b=2", xml)

    def test_feed_special_chars_valid_xml(self):
        feed = generators.gen_feed_xml(
            "黑哥 <AI> & 朋友",
            "https://heigeai.com/?utm_source=rss&utm_medium=feed",
            [("标题 & 符号", "Sat, 21 Jun 2026 00:00:00 GMT",
              "https://heigeai.com/a?x=1&y=2")],
            last_build="Sat, 21 Jun 2026 00:00:00 GMT")
        root = ET.fromstring(feed)
        # 转义后解析回来应还原原文
        self.assertEqual(root.find("./channel/title").text, "黑哥 <AI> & 朋友")

    def test_plain_inputs_unchanged(self):
        xml = generators.gen_sitemap([("https://x.com/", "2026-06-21")])
        self.assertIn("<loc>https://x.com/</loc>", xml)
        self.assertIn("<lastmod>2026-06-21</lastmod>", xml)


class TestAttributionUnparsedLines(unittest.TestCase):
    """[45] 解析不出 UA 字段的行要跳过,别把整行当 UA 扫出假命中。"""

    COMBINED = ('66.249.66.1 - - [x] "GET /pricing HTTP/1.1" 200 5123 "-" '
                '"Mozilla/5.0 (compatible; GPTBot/1.2)"')
    COMMON = '203.0.113.5 - - [x] "GET /blog/what-is-GPTBot-guide HTTP/1.1" 200 8000'

    def test_common_format_line_not_counted(self):
        r = attribution.parse_access_log(self.COMBINED + "\n" + self.COMMON)
        self.assertEqual(r["total_ai_hits"], 1)
        self.assertEqual(r["unparsed_lines"], 1)
        self.assertEqual(r["by_bot"][0]["hits"], 1)

    def test_all_common_warns_in_note(self):
        r = attribution.parse_access_log(self.COMMON + "\n" + self.COMMON)
        self.assertEqual(r["total_ai_hits"], 0)
        self.assertEqual(r["unparsed_lines"], 2)
        self.assertIn("警告", r["note"])

    def test_mostly_combined_no_warning(self):
        r = attribution.parse_access_log(self.COMBINED + "\n" + self.COMBINED + "\n" + self.COMMON)
        self.assertEqual(r["unparsed_lines"], 1)
        self.assertNotIn("警告", r["note"])

    def test_blank_lines_not_unparsed(self):
        r = attribution.parse_access_log("\n\n" + self.COMBINED + "\n\n")
        self.assertEqual(r["unparsed_lines"], 0)
        self.assertEqual(r["total_ai_hits"], 1)


if __name__ == "__main__":
    unittest.main()
