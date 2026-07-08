"""审查修复回归(cli-validate 组):findings 7/33/40/41/42/43/44。

覆盖 geo_cli.py(stdout 纯净性/reverse note)、validate.py(build-manifest sha256)、
platform_recommend.py(排序确定性/权重记账)、sourcing.py(层2兜底/cadence 空档)。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import platform_recommend as pr, sourcing  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import validate as validate_mod  # noqa: E402

CLI = os.path.join(ROOT, "scripts", "geo_cli.py")

PAGE = ('<html lang="zh"><head><title>测试页面标题达标十个字</title></head>'
        '<body><h1>标题</h1><p>本产品转化率提升30%,价格99元,服务10000名用户。</p>'
        '</body></html>')


def _run(args):
    return subprocess.run([sys.executable, CLI] + args, cwd=ROOT,
                          capture_output=True, text=True)


class TestPlaybookStdoutPurity(unittest.TestCase):
    """[7] --html 与 --json 同用时状态行不得污染 stdout。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.page = os.path.join(self.tmp, "page.html")
        with open(self.page, "w", encoding="utf-8") as fh:
            fh.write(PAGE)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_html_plus_json_stdout_is_pure_json(self):
        html_out = os.path.join(self.tmp, "pb.html")
        p = _run(["playbook", "--input", self.page, "--brand", "黑哥AI",
                  "--category", "AI培训", "--html", html_out, "--json"])
        self.assertEqual(p.returncode, 0, p.stderr)
        pb = json.loads(p.stdout)  # 首行是状态行时这里直接抛 JSONDecodeError
        self.assertIn("score_6dim", pb)
        # 交付物照常写出,状态行走 stderr
        self.assertTrue(os.path.isfile(html_out))
        self.assertIn("写入 HTML 作战手册", p.stderr)
        self.assertNotIn("写入 HTML 作战手册", p.stdout)


class TestReverseNoteInTextMode(unittest.TestCase):
    """[44] reverse 文本模式 0 命中时要把 note 带出来。"""

    def test_no_hit_prints_note(self):
        p = _run(["recommend", "--reverse", "不存在平台xyz"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("(0 个)", p.stdout)
        self.assertIn("未收录该平台", p.stdout)

    def test_hit_has_no_note_line(self):
        p = _run(["recommend", "--reverse", "知乎"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("未收录该平台", p.stdout)


class TestValidateBuildHashes(unittest.TestCase):
    """[33] validate 必须复算 build-manifest 的 sha256。"""

    def _write(self, d, rel, content):
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def test_mismatch_and_missing_detected(self):
        d = tempfile.mkdtemp()
        try:
            good = self._write(d, "scripts/geo_cli.py", "print('ok')\n")
            files = {"scripts/geo_cli.py": good, "gone.md": "0" * 64}
            msgs = validate_mod.manifest_hash_mismatches(files, d)
            self.assertEqual(len(msgs), 1)
            self.assertIn("缺失", msgs[0])
            # 内容被换掉 → 哈希不一致必须报
            self._write(d, "scripts/geo_cli.py", "// CORRUPTED PAYLOAD\n")
            msgs = validate_mod.manifest_hash_mismatches(files, d)
            self.assertEqual(len(msgs), 2)
            self.assertTrue(any("哈希不一致" in m for m in msgs))
        finally:
            shutil.rmtree(d)

    def test_matching_files_pass(self):
        d = tempfile.mkdtemp()
        try:
            h = self._write(d, "a.md", "内容")
            self.assertEqual(
                validate_mod.manifest_hash_mismatches({"a.md": h}, d), [])
        finally:
            shutil.rmtree(d)

    def test_real_adapters_consistent_with_manifest(self):
        # 仓库当前产物必须与 build-manifest 一致(即 [33] 的复现:换掉产物应被查出)
        bm_path = os.path.join(ROOT, "adapters", "build-manifest.json")
        with open(bm_path, encoding="utf-8") as fh:
            bm = json.load(fh)
        for adapter, rec in bm["adapters"].items():
            pkg = os.path.join(ROOT, "adapters", adapter, "heige-geo-seo")
            self.assertTrue(rec["files"], adapter)
            self.assertEqual(
                validate_mod.manifest_hash_mismatches(rec["files"], pkg), [],
                "%s 适配与 build-manifest 漂移" % adapter)


class TestRecommendDeterministicOrder(unittest.TestCase):
    """[40] 同分平台排名不得随 --engine 传入顺序漂移。"""

    def test_engine_order_permutation_same_ranking(self):
        a = [r["platform"] for r in pr.recommend(["豆包", "deepseek"])["recommendations"]]
        b = [r["platform"] for r in pr.recommend(["deepseek", "豆包"])["recommendations"]]
        self.assertEqual(a, b)

    def test_tie_broken_by_curated_rank(self):
        # 今日头条/搜狐/网易 同为 5 分 2 引擎,按权重表策展位次定名次
        rows = pr.recommend(["豆包", "deepseek"])["recommendations"]
        ties = [r["platform"] for r in rows if r["score"] == 5 and len(r["feeds_engines"]) == 2]
        self.assertEqual(ties, ["今日头条", "搜狐", "网易"])

    def test_curated_top_kept_for_single_engine(self):
        # 单引擎同分平台保持策展首位(Wikipedia 是 chatgpt 命脉,排前)
        r = pr.recommend(["chatgpt"])
        self.assertEqual(r["recommendations"][0]["platform"], "Wikipedia")

    def test_score_still_primary_key(self):
        rows = pr.recommend(["cn-all"])["recommendations"]
        scores = [r["score"] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestRationaleAccounting(unittest.TestCase):
    """[41] score 必须等于 sum(rationale.weight),content_type 加分也要入账。"""

    def _assert_books_balance(self, result):
        for row in result["recommendations"]:
            self.assertEqual(
                row["score"], sum(f["weight"] for f in row["rationale"]),
                "%s 记账不平" % row["platform"])

    def test_multi_engine_content_type_balances(self):
        # 审查复现场景:claude+perplexity+gemini + b2b 下 LinkedIn 曾 score=11 sum=15
        self._assert_books_balance(
            pr.recommend(["claude", "perplexity", "gemini"], content_type="b2b"))

    def test_plain_and_cn_content_type_balance(self):
        self._assert_books_balance(pr.recommend(["豆包", "元宝"]))
        self._assert_books_balance(pr.recommend(["豆包"], content_type="种草"))
        self._assert_books_balance(pr.recommend(["cn-all"], content_type="video"))

    def test_content_type_only_platform_keeps_engines(self):
        # 小红书只靠内容类型进表,feeds_engines 仍要给出真实目标引擎
        r = pr.recommend(["豆包"], content_type="种草")
        xhs = next(x for x in r["recommendations"] if x["platform"] == "小红书")
        self.assertEqual(xhs["feeds_engines"], ["豆包"])
        self.assertEqual(xhs["score"], 2)


class TestSourcingLayer2Fallback(unittest.TestCase):
    """[42] 不给 --engine 时层 2 收录动作不得静默为空。"""

    def test_no_engine_auto_market_gets_both_guides(self):
        p = sourcing.plan("咖啡机", ["咖啡机"], None)
        self.assertTrue(p["layer2_index"])
        joined = "\n".join(p["layer2_index"])
        self.assertIn("国内求收录", joined)
        self.assertIn("robots", joined)

    def test_explicit_market_stays_scoped(self):
        cn = "\n".join(sourcing.plan("x", ["y"], None, market="cn")["layer2_index"])
        self.assertIn("国内求收录", cn)
        self.assertNotIn("海外配 robots", cn)
        gl = "\n".join(sourcing.plan("x", ["y"], None, market="global")["layer2_index"])
        self.assertIn("robots", gl)
        self.assertNotIn("国内求收录", gl)


class TestSourcingCadence(unittest.TestCase):
    """[43] 引擎全未识别时 cadence 不得指向空档,描述随首档取词。"""

    def test_all_unrecognized_gives_corrective_cadence(self):
        p = sourcing.plan("咖啡机", ["咖啡机"], ["chatgtp"])
        cad = p["delivery_sop"]["cadence"]
        for tier in ("P0", "P1", "P2"):
            self.assertNotIn("先发 %s" % tier, cad)
            self.assertEqual(p["delivery_sop"]["tiers"][tier], [])
        self.assertIn("--engine", cad)

    def test_known_engine_cadence_matches_first_tier_label(self):
        p = sourcing.plan("x", ["y"], ["豆包"])
        self.assertTrue(p["delivery_sop"]["tiers"]["P0"])
        self.assertIn("先发 P0 首档(跨引擎共识/命脉平台)", p["delivery_sop"]["cadence"])

    def test_render_no_orphan_cadence_reference(self):
        # 渲染出的手册里,发布节奏行不再引用一个渲染时被跳过的空档
        md = sourcing.render_markdown(sourcing.plan("咖啡机", ["咖啡机"], ["chatgtp"]))
        self.assertNotIn("先发 P2 首档", md)
        self.assertIn("发布节奏:", md)


if __name__ == "__main__":
    unittest.main()
