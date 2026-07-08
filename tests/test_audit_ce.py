"""审查修复回归测试:content_engineering + playbook(findings 8/10/11/12/13/32/38)。"""
import unittest

import _path  # noqa: F401

from lib import htmldoc, playbook
from lib import content_engineering as ce


class TestQueryCoverageAsciiBoundary(unittest.TestCase):
    """[8] 英文短 gram 必须按 ASCII 边界匹配,不许裸子串误命中。"""

    def test_ai_not_hit_inside_training(self):
        # 正文没提 AI,'ai' 不许命中 training/email 的子串
        cov = ce._query_coverage("我们提供岗前 training 课程,细节请发 email。", ["AI 课程"])
        # 只有 CJK gram '课程' 命中,'ai' 不命中 → 覆盖率 0.5 而非 1.0
        self.assertEqual(cov, 0.5)

    def test_pure_english_doc_no_false_hit(self):
        cov = ce._query_coverage(
            "We offer training courses. Contact us via email for details.", ["AI 方案"])
        self.assertEqual(cov, 0.0)

    def test_real_ascii_mention_still_hits(self):
        # 真提到 AI(两侧是空格/CJK)必须照常命中
        self.assertEqual(ce._query_coverage("黑哥 AI 提供 AI 课程培训服务。", ["AI 课程"]), 1.0)
        self.assertEqual(ce._query_coverage("本文介绍AI课程的选型。", ["AI 课程"]), 1.0)

    def test_geo_not_hit_inside_geometry(self):
        self.assertEqual(ce._query_coverage("we study geometry here", ["GEO"]), 0.0)
        self.assertEqual(ce._query_coverage("GEO 优化指南", ["GEO"]), 1.0)


class TestDateStripKeepsNumericRanges(unittest.TestCase):
    """[10] _DATE_ANY 不许把价格/人数区间当日期吃掉。"""

    def test_ranges_survive(self):
        for text, nums in [("价格区间 5000-8000 元", ["5000", "8000"]),
                           ("预算 1000-2000 万", ["1000", "2000"]),
                           ("共 3000-5000 人参加", ["3000", "5000"])]:
            stripped = ce._strip_dates(text)
            self.assertEqual(ce._NUM.findall(stripped), nums, text)

    def test_real_dates_still_stripped(self):
        for text in ["发布于2026-06-01", "更新于2026年6月30日", "2026/6/1 上线", "1999年9月9日"]:
            stripped = ce._strip_dates(text)
            self.assertEqual(ce._NUM.findall(stripped), [], text)

    def test_year_like_range_start_not_matched_inside_longer_number(self):
        # 前导数字边界:12000-15 里的 2000-15 不许被当日期
        self.assertIn("12000-15", ce._strip_dates("库存 12000-15 号仓"))


class TestQuoteMarkPairingAndDedup(unittest.TestCase):
    """[11] 引号限单段严格配对,重复引语去重计数。"""

    def test_unclosed_quote_no_cross_paragraph(self):
        text = "第一段“未闭合\n第二段正文\n第三段:“这是真引用六个字”"
        hits = ce._QUOTE_MARK.findall(text)
        self.assertEqual(hits, ["“这是真引用六个字”"])

    def test_mismatched_quote_pair_rejected(self):
        # 「…” 这类错配不算引语
        self.assertEqual(ce._QUOTE_MARK.findall("「错配的引号内容六个字”"), [])

    def test_repeated_quote_counted_once(self):
        base = "<html><body><h1>产品介绍</h1><p>本产品提供智能写作功能。</p>"
        plain = ce.score(htmldoc.from_string(base + "</body></html>"))
        spam = ce.score(htmldoc.from_string(
            base + "<p>" + "“这里是六个字以上的空话引语”" * 20 + "</p></body></html>"))
        plain_aq = [r for r in plain["elements"] if r["key"] == "authority_quote"][0]
        spam_aq = [r for r in spam["elements"] if r["key"] == "authority_quote"][0]
        # 复制 20 遍不许把 authority_quote 刷满
        self.assertLess(spam_aq["score_0_1"], 1.0)
        # 总分不许因垃圾重复引语大幅上涨(修复前 12.8 → 23.3)
        self.assertLess(spam["score"], plain["score"] + 3)

    def test_distinct_quotes_still_counted(self):
        text = "专家称:“第一条真实的引语内容”。另一位指出:“第二条不同的引语内容”。"
        self.assertEqual(len(set(ce._QUOTE_MARK.findall(text))), 2)


class TestAnnotateMultilineHeading(unittest.TestCase):
    """[38] 跨行标题规整空白后必须被识别为标题。"""

    def test_multiline_heading_recognized(self):
        d = htmldoc.from_string(
            "<html><body><h2>多行\n标题文字</h2><p>正文段落在这里说明产品。</p></body></html>")
        rows = ce.annotate(d)["paragraphs"]
        by_preview = {r["preview"]: r["is_heading"] for r in rows}
        self.assertTrue(by_preview["多行"])
        self.assertTrue(by_preview["标题文字"])
        self.assertFalse(by_preview["正文段落在这里说明产品。"])

    def test_single_line_heading_still_recognized(self):
        d = htmldoc.from_string("<html><body><h2>单行标题</h2><p>正文。</p></body></html>")
        rows = ce.annotate(d)["paragraphs"]
        self.assertTrue([r for r in rows if r["preview"] == "单行标题"][0]["is_heading"])
        self.assertFalse([r for r in rows if r["preview"] == "正文。"][0]["is_heading"])


_STRONG_CN = ("<html lang=\"zh\"><head><title>公众号排版工具评测报告二〇二六</title></head><body>"
              "<h1>公众号排版工具评测</h1><h2>结论摘要</h2>"
              "<p>摘要:本文评测了十二款国产排版工具,覆盖办公、写作两大场景。</p>"
              "<p>据艾瑞咨询报告显示,行业渗透率达到 37%,头部工具月活超过 500 万。</p>"
              "<p>专家指出:“排版效率直接决定内容生产速度”。来源:艾瑞咨询 2026 年白皮书。</p>"
              "<ul><li>要点一:支持一键排版</li><li>要点二:适配深色模式</li></ul>"
              "<p>常见问题:什么是智能排版?智能排版是指用算法自动完成版式设计的技术。</p>"
              "<p>本方案适用于中小团队场景,应用案例包括教育、电商行业。</p>"
              "</body></html>")

_WEAK_CN = "<html><body><p>随便写点没有数据的内容。</p></body></html>"


class TestCompareWeightedGapSort(unittest.TestCase):
    """[12] compare 差距排序必须按 gap×权重,与 cescore weakest 口径统一。"""

    def test_gaps_sorted_by_weighted_gap(self):
        c = playbook.compare([("你", htmldoc.from_string(_WEAK_CN)),
                              ("强竞", htmldoc.from_string(_STRONG_CN))])
        gaps = c["gaps"]
        self.assertGreater(len(gaps), 1)
        weighted = [g["weighted_gap"] for g in gaps]
        self.assertEqual(weighted, sorted(weighted, reverse=True))
        # 每条差距都带权重与加权欠分,且口径一致
        for g in gaps:
            self.assertAlmostEqual(g["weighted_gap"], round(g["gap"] * g["weight"], 2), places=1)

    def test_low_weight_full_gap_not_ranked_above_high_weight(self):
        # 权重 4 的跨域贡献即使 gap=1.0(加权 4.0),也不许排在加权欠分更大的高权重要素前面
        c = playbook.compare([("你", htmldoc.from_string(_WEAK_CN)),
                              ("强竞", htmldoc.from_string(_STRONG_CN))])
        pos = {g["element"]: i for i, g in enumerate(c["gaps"])}
        if "跨域贡献" in pos and "统计数据" in pos:
            self.assertLess(pos["统计数据"], pos["跨域贡献"])

    def test_render_compare_shows_weighted_order(self):
        md = playbook.render_compare(playbook.compare(
            [("你", htmldoc.from_string(_WEAK_CN)), ("强竞", htmldoc.from_string(_STRONG_CN))]))
        self.assertIn("加权欠分", md)


class TestPlaybookMarketPropagation(unittest.TestCase):
    """[13/32] generate 必须把解析后的 eff_market 传给 sourcing,单一市场口径。"""

    def test_auto_market_resolved_consistently(self):
        pb = playbook.generate(htmldoc.from_string(_STRONG_CN),
                               brand="黑哥AI", category="AI培训", market="auto")
        self.assertEqual(pb["market"], "cn")
        self.assertEqual(pb["sourcing"]["market"], "cn")

    def test_cn_page_auto_market_layer2_actions_not_empty(self):
        # 真实中文页 market=auto 且不带引擎:层 2 收录前置动作(百度推送/ICP)不许为空
        pb = playbook.generate(htmldoc.from_string(_STRONG_CN),
                               brand="黑哥AI", category="AI培训", market="auto")
        self.assertTrue(pb["sourcing"]["layer2_index"])

    def test_markdown_single_market_label(self):
        pb = playbook.generate(htmldoc.from_string(_STRONG_CN),
                               brand="黑哥AI", category="AI培训", market="auto")
        md = playbook.render_markdown(pb)
        market_lines = [ln for ln in md.split("\n") if "市场" in ln and "auto" in ln]
        self.assertEqual(market_lines, [])

    def test_explicit_market_still_respected(self):
        pb = playbook.generate(htmldoc.from_string(_STRONG_CN),
                               brand="X", category="tool", market="global")
        self.assertEqual(pb["sourcing"]["market"], "global")


if __name__ == "__main__":
    unittest.main()
