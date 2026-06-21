"""「为何没被引用」诊断器:7 条引用失败根因的确定性检查。

来自对成熟监控 SaaS(Profound/Brandlight)的逆向:它们靠黑盒给结论,
我方做成可解释、可复现的确定性清单,每条 pass/fail + 具体修复动作。
另含国内 ICP 备案检测(国产引擎收录独立站的前置门槛)。
纯标准库。
"""

import re

from . import scoring


_ANSWER_WORDS_MIN = 30
_ANSWER_WORDS_MAX = 90  # 中文按字符近似,放宽到 30~90


def _first_block_len(doc):
    text = doc.text.replace("\n", " ").strip()
    # take up to first sentence boundary cluster
    seg = re.split(r"[。!?!?]", text, 1)
    head = seg[0] if seg else text
    cjk = len(re.findall(r"[一-鿿]", head))
    latin = len(re.findall(r"[A-Za-z][A-Za-z'-]*", head))
    return cjk + latin


def diagnose(doc, market="auto"):
    if market == "auto":
        market = "cn" if doc.is_cjk else "global"
    jl = scoring.analyze_jsonld(doc.jsonld_blocks)
    findings = []

    def add(cause, ok, fix):
        findings.append({"cause": cause, "status": "pass" if ok else "fail",
                         "fix": "" if ok else fix})

    # 1. canonical 正确
    add("canonical 缺失或不规范", bool(doc.canonical),
        "每页 <head> 加 <link rel=\"canonical\">,指向规范 URL,避免 AI 引到错误变体")

    # 2. 实体命名一致(单页近似:Organization name 是否出现在正文/title)
    org_names = []
    for p in jl["parsed"]:
        scoring._find_nodes(p, "Organization", org_names)
    org_name = next((n.get("name") for n in org_names if isinstance(n.get("name"), str)), None)
    consistent = (org_name is None) or (org_name in doc.text or org_name in doc.title)
    add("实体命名跨位置不一致", consistent,
        "统一品牌名在 schema、title、正文里的写法,消除 AI 实体消歧障碍")

    # 3. Organization/Person 来源标注
    has_org = "Organization" in jl["types"]
    has_person = "Person" in jl["types"]
    add("缺 Organization/Person 来源标注", has_org or has_person,
        "补 Organization + Person(作者)schema,带 @id 可信链,让 AI 能溯源归因")

    # 4. 机器可读关系弱(sameAs / 足量 schema)
    has_sameas = scoring._has_sameas(jl["parsed"])
    add("机器可读关系弱(无 sameAs)", has_sameas,
        "给 Organization/Person 补 sameAs 到 Wikipedia/Wikidata/LinkedIn,建实体关系")

    # 5. 缺 40-60 词自包含答案块
    head_len = _first_block_len(doc)
    has_answer = _ANSWER_WORDS_MIN <= head_len <= _ANSWER_WORDS_MAX or head_len >= _ANSWER_WORDS_MIN
    add("开头缺自包含答案块", _ANSWER_WORDS_MIN <= head_len <= _ANSWER_WORDS_MAX,
        "页面/每节开头放 40-60 词自包含直接答案(中文 30~90 字),主谓宾齐全可整句抽走")

    # 6. 缺 FAQ schema
    add("缺 FAQPage schema", "FAQPage" in jl["types"],
        "把真实问答对做成 FAQPage JSON-LD(实测 2.7x 引用率)")

    # 7. 信息缺口(单页不可判,标为人工核验)
    findings.append({"cause": "信息缺口(你没回答→AI 引竞品)", "status": "manual",
                     "fix": "对比目标 prompt 集里你没覆盖的问题,补内容。需跑 prompt 覆盖率(prompts + sov 模块)"})

    # 国内 ICP 备案(cn 市场前置门槛)
    if market == "cn":
        beian = bool(re.search(r"(ICP备|ICP证|京ICP|粤ICP|沪ICP|beian\.miit\.gov\.cn|网安备)",
                               doc.raw, re.IGNORECASE))
        findings.append({"cause": "ICP/网安备案信号缺失(国内收录前置门槛)",
                         "status": "pass" if beian else "warn",
                         "fix": "" if beian else "国内独立站须完成 ICP 备案并在页脚展示备案号,不备案被国产 AI 收录基本归零"})

    failed = [f for f in findings if f["status"] == "fail"]
    return {
        "market": market,
        "root_causes_checked": len(findings),
        "failed_count": len(failed),
        "findings": findings,
        "verdict": "可被引用障碍较多" if len(failed) >= 3 else
                   ("有改进空间" if failed else "无明显引用失败根因"),
    }
