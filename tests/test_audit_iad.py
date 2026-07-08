"""审查修复回归测试:intent / agent_readiness / diagnose 任务组。

覆盖 findings [21][22][23/35][24/31]:
- [21] 「怎么买/哪里买」被 informational 的「怎么」抢走判信息型
- [22] 「试用」子串误命中「面试用/考试用」
- [23/35] agent_readiness 关键动作大小写敏感裸子串匹配(误报+漏报双向)
- [24/31] diagnose 根因5 分句不认半角句号致英文页必 fail,且首块混入导航文本
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, intent, sourcing, agent_readiness, diagnose  # noqa: E402
from lib.diagnose import _first_block_len  # noqa: E402


class TestIntentBuySignals(unittest.TestCase):
    """[21] 交易意图信号补齐 + 跨意图最长信号压制。"""

    def test_all_sourcing_transactional_templates_classified_transactional(self):
        # sourcing 的四条交易模板必须全部被 intent 判成 transactional
        for tmpl in sourcing._INTENT_TEMPLATES["交易"]:
            q = tmpl.format(r="咖啡机")
            self.assertEqual(intent.classify(q)["intent"], "transactional",
                             "交易模板 %r 未被判为交易意图" % q)

    def test_zenmemai_beats_informational_zenme(self):
        r = intent.classify("咖啡机怎么买")
        self.assertEqual(r["intent"], "transactional")
        self.assertIn("怎么买", r["signals_matched"])
        # 「怎么」被更长的「怎么买」跨意图压制,informational 不再计分
        self.assertEqual(r["all_scores"]["informational"], 0)

    def test_nalimai_matched(self):
        r = intent.classify("咖啡机哪里买")
        self.assertEqual(r["intent"], "transactional")
        self.assertIn("哪里买", r["signals_matched"])

    def test_plain_zenme_still_informational(self):
        # 没有更长交易信号时「怎么」照常给信息型计分
        self.assertEqual(intent.classify("咖啡机怎么除垢")["intent"],
                         "informational")


class TestIntentShiyongLeftGuard(unittest.TestCase):
    """[22] 「试用」左邻构词字检查。"""

    def test_mianshi_kaoshi_not_transactional(self):
        for q in ["面试用什么软件好", "考试用什么笔", "面试用英语怎么自我介绍"]:
            r = intent.classify(q)
            self.assertNotIn("试用", r["signals_matched"],
                             "%r 误命中「试用」" % q)
            self.assertNotEqual(r["intent"], "transactional",
                                "%r 被误判为交易意图" % q)

    def test_real_shiyong_still_matched(self):
        for q in ["免费试用装哪里领", "产品可以申请试用吗", "试用一下这个工具"]:
            self.assertIn("试用", intent.classify(q)["signals_matched"],
                          "%r 应命中「试用」" % q)

    def test_blocked_then_valid_occurrence_still_matched(self):
        # 同一查询里第一次命中被左邻挡掉、第二次是真「试用」时仍要计分
        self.assertIn("试用",
                      intent.classify("面试用的软件能免费试用吗")["signals_matched"])


class TestAgentReadinessKeyAction(unittest.TestCase):
    """[23/35] 关键动作识别:动作节点扫描 + 大小写不敏感 + ASCII 边界。"""

    @staticmethod
    def _action_check(html):
        r = agent_readiness.audit(htmldoc.from_string(html))
        return [c for c in r["checks"] if c["name"] == "关键动作可被机器识别"][0]

    def test_facebook_link_not_false_positive(self):
        # facebook 含 book 子串,边界匹配下不算命中
        c = self._action_check(
            '<html><body><p>Follow us on '
            '<a href="https://facebook.com/x">Facebook</a></p></body></html>')
        self.assertEqual(c["status"], "fail")

    def test_image_filename_and_alt_not_scanned(self):
        # 图片文件名 bulk-buy-poster.jpg 和 alt「下单按钮」都不算动作节点
        c = self._action_check(
            '<html><body><img src="/images/community-bulk-buy-poster.jpg" '
            'alt="下单按钮"><img src="/x/travel-booking-light.jpg"></body></html>')
        self.assertEqual(c["status"], "fail")

    def test_capitalized_english_cta_recognized(self):
        c = self._action_check(
            '<html><body><button>Buy Now</button>'
            '<a href="/demo">Book a Demo</a>'
            '<a href="/account/new">Register</a></body></html>')
        self.assertEqual(c["status"], "pass")

    def test_score_case_insensitive(self):
        # 同一表单页大小写两个版本得分必须一致([35] 曾差 20 分跨档)
        html = ('<html><body><form><label for=e>Email</label>'
                '<input name=email id=e>'
                '<button type=submit>Sign Up Now</button></form>'
                '<div role=main aria-label=x></div></body></html>')
        r1 = agent_readiness.audit(htmldoc.from_string(html))
        r2 = agent_readiness.audit(
            htmldoc.from_string(html.replace("Sign Up Now", "sign up now")))
        self.assertEqual(r1["score"], r2["score"])
        self.assertEqual(r1["grade"], "就绪")

    def test_cjk_cta_in_button_recognized(self):
        c = self._action_check(
            "<html><body><a href='/order'>立即购买</a></body></html>")
        self.assertEqual(c["status"], "pass")

    def test_input_value_cta_recognized(self):
        c = self._action_check(
            "<html><body><form><input type=submit value='提交'></form>"
            "</body></html>")
        self.assertEqual(c["status"], "pass")


class TestDiagnoseFirstBlock(unittest.TestCase):
    """[24/31] 根因5 自包含答案块:英文句号切分 + 跳过 h1 前导航文本。"""

    _EN_FIRST = ("HeiGe GEO SEO is an offline toolkit that scores web pages "
                 "for AI citation readiness, generates robots and llms files, "
                 "and audits schema markup so that large language models can "
                 "discover, parse and cite your content reliably across "
                 "ChatGPT Perplexity and Gemini engines today.")

    @staticmethod
    def _answer_finding(doc):
        return [f for f in diagnose.diagnose(doc)["findings"]
                if f["cause"] == "开头缺自包含答案块"][0]

    def test_english_answer_first_page_passes(self):
        rest = " ".join("Additional paragraph number %d explains more "
                        "details about the toolkit." % i for i in range(30))
        doc = htmldoc.from_string(
            '<html lang="en"><body><h1>H</h1><p>%s</p><p>%s</p></body></html>'
            % (self._EN_FIRST, rest))
        self.assertEqual(_first_block_len(doc), 44)
        self.assertEqual(self._answer_finding(doc)["status"], "pass")

    def test_decimal_and_domain_not_split(self):
        # 小数 3.5 和域名 heigeai.com 里的句点不算句界
        doc = htmldoc.from_string(
            "<html><body><h1>报告</h1><p>本方案把加载速度提升了3.5倍,详情见 "
            "heigeai.com 官网,覆盖两千家企业客户与三十个行业场景,含完整口径和"
            "复现步骤。后面还有很多正文。</p></body></html>")
        # 首句 46 字(含 heigeai/com 两个 latin 词),没有被拆成小数残句
        self.assertEqual(_first_block_len(doc), 46)

    def test_nav_text_before_h1_skipped(self):
        # h1 之前的导航文本不进「首块」度量
        nav = "".join("<a href='/x%d'>栏目%d</a>" % (i, i) for i in range(20))
        answer = ("黑哥GEO工具是一套离线评分系统,吃一张网页就能给出六维二十二项"
                  "的引用就绪度评分,并产出机器人文件与结构化数据整改清单。")
        doc = htmldoc.from_string(
            "<html><body><nav>%s</nav><h1>黑哥GEO工具</h1><p>%s</p>"
            "</body></html>" % (nav, answer))
        # 40 条导航文本(每条 3 字)若混入首块必超 90 上限;跳过后落在 30~90 区间
        self.assertTrue(30 <= _first_block_len(doc) <= 90,
                        "首块长度 %d 不在 30~90" % _first_block_len(doc))
        self.assertEqual(self._answer_finding(doc)["status"], "pass")

    def test_no_h1_falls_back_to_full_text(self):
        doc = htmldoc.from_string(
            "<html><body><p>只有一句很短的话。</p></body></html>")
        self.assertGreater(_first_block_len(doc), 0)
        self.assertEqual(self._answer_finding(doc)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
