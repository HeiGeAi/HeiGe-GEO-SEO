"""审查修复回归测试(scoring 组):findings [4] unknown 三态 / [6] D5 同站过滤 / [37] 空 JSON-LD 块。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, scoring  # noqa: E402


def _doc(body, head=""):
    return htmldoc.from_string("<html><head>%s</head><body>%s</body></html>" % (head, body))


def _check(result, cid):
    for d in result["dimensions"]:
        for c in d["checks"]:
            if c["id"] == cid:
                return c
    raise AssertionError("check %s not found" % cid)


BODY = "<h1>标题</h1><p>" + "产品转化率提升了30%,价格99元,用户超过10000人。" * 20 + "</p>"


class TestUnknownExcluded(unittest.TestCase):
    """[4] 缺输入的 check 标 unknown 并从分母剔除,不编造 fail 理由。"""

    def test_b4_unknown_without_robots(self):
        # 只给 llms 不给 robots:B4 不该断言「robots 未声明 Sitemap」
        r = scoring.score_document(_doc(BODY), robots_text=None, llms_text="# 站点\n")
        b4 = _check(r, "B4")
        self.assertEqual(b4["status"], "unknown")
        self.assertNotIn("未声明", b4["note"])

    def test_b2_b3_unknown_when_not_probed(self):
        # llms_full/ai_txt 默认 None=未检测 -> unknown;显式 False=检测过不存在 -> fail
        r = scoring.score_document(_doc(BODY), llms_text="# 站点\n")
        self.assertEqual(_check(r, "B2")["status"], "unknown")
        self.assertEqual(_check(r, "B3")["status"], "unknown")
        r2 = scoring.score_document(_doc(BODY), llms_text="# 站点\n",
                                    llms_full=False, ai_txt=False)
        self.assertEqual(_check(r2, "B2")["status"], "fail")
        self.assertEqual(_check(r2, "B3")["status"], "fail")

    def test_unknown_weight_out_of_denominator(self):
        # llms-only:B 维度只有 B1(8 分)进分母,B2/B3/B4 的 8 分剔除
        r = scoring.score_document(_doc(BODY), llms_text="# 站点\n")
        bdim = next(d for d in r["dimensions"] if d["key"] == "B")
        self.assertEqual(bdim["weight_evaluated"], 8)
        known_w = sum(c["weight"] for d in r["dimensions"] for c in d["checks"]
                      if c["status"] != "unknown")
        self.assertEqual(r["included_weight"], known_w)

    def test_unknown_scores_higher_than_explicit_fail(self):
        # 未检测(unknown 剔分母)不该和「检测过且不存在」(fail 进分母)一个分:
        # 缺输入不当硬伤扣分
        base = _doc(BODY)
        r_unknown = scoring.score_document(base, llms_text="# 站点\n")
        r_fail = scoring.score_document(base, llms_text="# 站点\n",
                                        llms_full=False, ai_txt=False)
        self.assertGreater(r_unknown["score"], r_fail["score"])

    def test_unknown_not_in_weakest(self):
        r = scoring.score_document(_doc(BODY), llms_text="# 站点\n")
        self.assertNotIn("B4", [w["id"] for w in r["weakest"]])

    def test_b4_still_fails_when_robots_lacks_sitemap(self):
        # 提供了 robots 且确实没声明 Sitemap:照旧 fail,unknown 只给缺输入
        r = scoring.score_document(_doc(BODY), robots_text="User-agent: *\nAllow: /\n")
        self.assertEqual(_check(r, "B4")["status"], "fail")


class TestD5SameHostFilter(unittest.TestCase):
    """[6] 指向本站的绝对 URL(WordPress 式)不算外部引用。"""

    CANON = '<link rel="canonical" href="https://www.example.com/a">'

    def test_same_host_links_not_external(self):
        body = ('<h1>产品页</h1><p>本产品转化率提升了30%,价格99元,用户超过10000人。</p>'
                '<p><a href="https://www.example.com/pricing">价格</a>'
                '<a href="https://www.example.com/about">关于</a></p>')
        r = scoring.score_document(_doc(body, head=self.CANON))
        d5 = _check(r, "D5")
        self.assertIn("外链 0 个", d5["note"])
        self.assertEqual(d5["earned"], 2.0)  # 只剩数字信号,拿不到满分 4

    def test_www_normalized_both_directions(self):
        # canonical 带 www、链接不带 www(或反过来)都判同站
        body = ('<h1>x</h1><p>转化率30%,价格99元,用户10000人。</p>'
                '<a href="https://example.com/p">p</a>')
        r = scoring.score_document(_doc(body, head=self.CANON))
        self.assertIn("外链 0 个", _check(r, "D5")["note"])

    def test_real_external_link_still_counts(self):
        body = ('<h1>x</h1><p>转化率30%,价格99元,用户10000人。</p>'
                '<a href="https://zh.wikipedia.org/wiki/x">维基</a>')
        r = scoring.score_document(_doc(body, head=self.CANON))
        d5 = _check(r, "D5")
        self.assertEqual(d5["earned"], 4.0)
        self.assertIn("外链 1 个", d5["note"])

    def test_og_url_fallback(self):
        # 无 canonical 时用 og:url 推本站域名
        head = '<meta property="og:url" content="https://example.com/a">'
        body = ('<h1>x</h1><p>转化率30%,价格99元,用户10000人。</p>'
                '<a href="https://www.example.com/p">p</a>')
        r = scoring.score_document(_doc(body, head=head))
        self.assertIn("外链 0 个", _check(r, "D5")["note"])

    def test_no_host_info_keeps_behavior_with_note(self):
        # 推不出本站域名:保持原计数,note 说明未过滤
        body = ('<h1>x</h1><p>转化率30%,价格99元,用户10000人。</p>'
                '<a href="https://somewhere.com/p">p</a>')
        r = scoring.score_document(_doc(body))
        d5 = _check(r, "D5")
        self.assertIn("外链 1 个", d5["note"])
        self.assertIn("未按本站域名过滤", d5["note"])


class TestEmptyJsonldBlock(unittest.TestCase):
    """[37] 空/纯空白 ld+json 块跳过,不拖垮 C4。"""

    VALID = ('<script type="application/ld+json">{"@context":"https://schema.org",'
             '"@type":"Organization","name":"黑哥AI","url":"x","logo":"x",'
             '"description":"d"}</script>')

    def test_empty_block_does_not_zero_c4(self):
        body = ('<h1>页面</h1><p>介绍内容。</p>'
                '<script type="application/ld+json"></script>' + self.VALID)
        r = scoring.score_document(_doc(body))
        c4 = _check(r, "C4")
        self.assertEqual(c4["earned"], 3.0)
        self.assertNotIn("报错", c4["note"])

    def test_whitespace_block_skipped(self):
        jl = scoring.analyze_jsonld(["   \n  ", '{"@type": "Organization"}'])
        self.assertFalse(jl["has_error"])
        self.assertEqual(jl["block_count"], 1)
        self.assertIn("Organization", jl["types"])

    def test_only_empty_blocks_means_no_jsonld(self):
        # 全是空块 = 页面无 JSON-LD,C4 走「页面无 JSON-LD」而非「解析报错」
        body = ('<h1>页面</h1><p>介绍内容。</p>'
                '<script type="application/ld+json"></script>')
        r = scoring.score_document(_doc(body))
        c4 = _check(r, "C4")
        self.assertEqual(c4["earned"], 0.0)
        self.assertIn("无 JSON-LD", c4["note"])

    def test_truly_broken_block_still_errors(self):
        # 非空但非法的块照旧记解析报错,别把修复做成一刀切放行
        jl = scoring.analyze_jsonld(["{broken json"])
        self.assertTrue(jl["has_error"])


if __name__ == "__main__":
    unittest.main()
