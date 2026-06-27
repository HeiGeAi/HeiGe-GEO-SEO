"""v1.7 测试:信源策略层 sourcing + cescore 闭环(--query 真需求匹配 + --annotate 段落级)。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import sourcing, content_engineering as ce, htmldoc  # noqa: E402


DOC = """<html lang="zh"><head><title>公众号排版工具怎么选</title></head><body>
<h1>2026 公众号排版工具怎么选,哪个好</h1>
<p>摘要:据某行业报告,90% 运营者用排版工具提效。本文给出排版工具对比结论。</p>
<h2>核心结论</h2><ul><li>追求免费选 A,实测 3 分钟出图</li></ul>
<h2>常见问题 FAQ</h2><p>问:排版工具多少钱?答:基础版免费,来源 https://example.com 。</p>
<p>排版是指内容视觉编排。本测试由有 10 年经验团队完成,更新于 2026-06-01。</p>
</body></html>"""


class TestSourcing(unittest.TestCase):
    def test_plan_structure(self):
        p = sourcing.plan("公众号排版工具", ["公众号排版"], ["豆包", "元宝"])
        for k in ("layer2_index", "layer3_query_matrix", "layer4_source_preference",
                  "delivery_sop", "diagnosis_loop"):
            self.assertIn(k, p)
        self.assertEqual(p["market"], "cn")  # 纯国产引擎

    def test_query_matrix_per_root(self):
        p = sourcing.plan("x", ["排版工具", "公众号"], ["豆包"])
        roots = [r["root"] for r in p["layer3_query_matrix"]]
        self.assertEqual(roots, ["排版工具", "公众号"])
        # 三类意图都在
        self.assertEqual(set(p["layer3_query_matrix"][0]["by_intent"].keys()),
                         {"信息", "商业", "交易"})

    def test_reuses_recommend_weights(self):
        p = sourcing.plan("x", ["y"], ["豆包"])
        plats = [r["platform"] for r in p["layer4_source_preference"]]
        self.assertIn("今日头条", plats)  # 豆包字节系自有池

    def test_tiers_consensus_to_p0(self):
        # 搜狐同时喂豆包+元宝 → 跨引擎共识进 P0
        p = sourcing.plan("x", ["y"], ["豆包", "元宝"])
        p0 = [it["platform"] for it in p["delivery_sop"]["tiers"]["P0"]]
        self.assertIn("搜狐", p0)

    def test_overseas_market(self):
        p = sourcing.plan("x", ["y"], ["chatgpt", "perplexity"])
        self.assertEqual(p["market"], "global")

    def test_render(self):
        md = sourcing.render_markdown(sourcing.plan("公众号排版", ["排版"], ["豆包"]))
        self.assertIn("信源策略规划", md)
        self.assertIn("词根→问句矩阵", md)

    def test_empty_engines_no_crash(self):
        p = sourcing.plan("x", ["y"], None)
        self.assertEqual(p["layer4_source_preference"], [])


class TestCescoreQuery(unittest.TestCase):
    def test_query_raises_confidence(self):
        doc = htmldoc.from_string(DOC)
        no_q = ce.score(doc)
        with_q = ce.score(doc, queries=["公众号排版工具哪个好", "最好的排版工具"])
        sem_no = next(e for e in no_q["elements"] if e["key"] == "semantic")
        sem_q = next(e for e in with_q["elements"] if e["key"] == "semantic")
        self.assertTrue(sem_no["low_confidence"])
        self.assertFalse(sem_q["low_confidence"])  # 有 query 高置信
        self.assertIsNotNone(with_q["query_coverage"])
        self.assertIsNone(no_q["query_coverage"])

    def test_query_coverage_responds(self):
        doc = htmldoc.from_string(DOC)
        # 相关问句覆盖率应高于无关问句
        related = ce.score(doc, queries=["公众号排版工具哪个好"])["query_coverage"]
        unrelated = ce.score(doc, queries=["量子计算机原理是什么"])["query_coverage"]
        self.assertGreater(related, unrelated)

    def test_query_makes_semantic_eligible_for_weakest(self):
        # 证据齐全但 query 完全不覆盖 → 语义是最弱项;无 query 被排除,有 query 进排序
        rich = ("<html lang='zh'><head><title>方法</title></head><body><h1>方法论标题</h1>"
                "<p>摘要:据《行业白皮书》研究,见 https://a.com 。来源:https://b.com 。转化率 87%。</p>"
                "<h2>结论</h2><ul><li>要点</li></ul>"
                "<p>常见问题FAQ:方法是指流程。多源交叉验证,本文更新于 2026-06-01。"
                "适用场景:案例已覆盖,有10年经验团队。</p></body></html>")
        doc = htmldoc.from_string(rich)
        no_q = [w["element"] for w in ce.score(doc)["weakest"]]
        with_q = [w["element"] for w in ce.score(doc, queries=["太空探索火箭原理是什么"])["weakest"]]
        self.assertNotIn("语义密度/需求匹配", no_q)   # 无 query:低置信被排除
        self.assertIn("语义密度/需求匹配", with_q)     # 有 query:高置信且最弱,进排序


class TestCescoreAnnotate(unittest.TestCase):
    def test_annotate_structure(self):
        ann = ce.annotate(htmldoc.from_string(DOC))
        self.assertGreater(ann["paragraph_count"], 0)
        for p in ann["paragraphs"]:
            self.assertIn("elements_present", p)
            self.assertIn("tip", p)

    def test_evidence_rich_para_tagged(self):
        ann = ce.annotate(htmldoc.from_string(DOC))
        # "据某行业报告,90%...对比结论" 段应承载统计数据
        joined = " ".join("".join(p["elements_present"]) for p in ann["paragraphs"])
        self.assertIn("统计数据", joined)

    def test_annotate_empty_no_crash(self):
        ann = ce.annotate(htmldoc.from_string(""))
        self.assertEqual(ann["paragraph_count"], 0)


class TestV17ReviewFixes(unittest.TestCase):
    """v1.7 复审挖出的真问题的回归测试。"""

    def test_single_engine_lifeline_in_p0(self):
        # 单引擎豆包:命脉今日头条/抖音(加权3=本次最高)应进 P0,不被降级
        p = sourcing.plan("x", ["y"], ["豆包"])
        p0 = [it["platform"] for it in p["delivery_sop"]["tiers"]["P0"]]
        self.assertIn("今日头条", p0)
        self.assertTrue(len(p["delivery_sop"]["tiers"]["P0"]) > 0)  # P0 不恒空

    def test_single_engine_gemini_youtube_p0(self):
        p = sourcing.plan("x", ["y"], ["gemini"])
        p0 = [it["platform"] for it in p["delivery_sop"]["tiers"]["P0"]]
        self.assertIn("YouTube", p0)  # gemini 命脉

    def test_unrecognized_engine_surfaced(self):
        p = sourcing.plan("x", ["y"], ["不存在的引擎"])
        self.assertIn("不存在的引擎", p["unrecognized_engines"])
        # 全未识别时收录指引兜底给国内+海外,不空
        self.assertTrue(len(p["layer2_index"]) > 0)

    def test_known_engine_no_false_unrecognized(self):
        p = sourcing.plan("x", ["y"], ["豆包"])
        self.assertIsNone(p["unrecognized_engines"])

    def test_no_gram_query_semantic_low_conf(self):
        # 退化 query(切不出检索单元)→ 语义应仍低置信,query_coverage 为 None,口径自洽
        doc = htmldoc.from_string(DOC)
        r = ce.score(doc, queries=["??"])
        sem = next(e for e in r["elements"] if e["key"] == "semantic")
        self.assertTrue(sem["low_confidence"])
        self.assertIsNone(r["query_coverage"])

    def test_weakest_prioritizes_high_weight_gap(self):
        # 高权重证据层缺口应排在低权重缺口之前(加权欠分排序)
        doc = htmldoc.from_string("<html><body><p>一段没有证据没有数字的普通陈述文字。</p></body></html>")
        names = [w["element"] for w in ce.score(doc)["weakest"]]
        # 权威原文引语(16%)应排在易懂表达(3%)之前
        self.assertIn("权威原文引语", names)

    def test_title_not_in_body_text(self):
        doc = htmldoc.from_string(
            "<html><head><title>这是标题党文案</title></head><body><p>这是正文内容。</p></body></html>")
        self.assertNotIn("这是标题党文案", doc.text)
        self.assertEqual(doc.title, "这是标题党文案")


class TestV17Cli(unittest.TestCase):
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

    def test_sourcing_cli(self):
        rc, out = self._run(["sourcing", "--category", "排版工具", "--root", "排版",
                             "--engine", "豆包", "--json"])
        self.assertEqual(rc, 0)
        self.assertIn("layer4_source_preference", out)

    def test_cescore_query_cli(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "_ce17.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(DOC)
        try:
            rc, out = self._run(["cescore", "--input", path, "--query", "排版工具哪个好", "--json"])
            import json
            self.assertEqual(rc, 0)
            self.assertIsNotNone(json.loads(out)["query_coverage"])
        finally:
            os.remove(path)

    def test_cescore_annotate_cli(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "_ce17b.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(DOC)
        try:
            rc, out = self._run(["cescore", "--input", path, "--annotate", "--json"])
            import json
            self.assertEqual(rc, 0)
            self.assertIn("paragraphs", json.loads(out))
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
