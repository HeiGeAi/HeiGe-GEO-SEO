"""监测采集闭环(八层第 8 层治理/反馈)。

会议方法论:监测=概率。一个问句、一个平台、同样方式重复检索 5 次,跑约 5 个平台,
共约 25 次,取均值=品牌被推荐概率,优化 GEO 本质是把这个概率从 A 提到 B。

本模块两件事:
  1. collection_kit:产出采集工具包——采样协议 + records.json 模板/schema + 要问的
     buyer prompt 集 + 喂回哪些命令。度量学离线,采集寄生宿主 agent(Claude/人工带浏览器)。
  2. measure_all:一键把采集回来的 records 同时喂 sov(占位)+ lostprompt(竞品夺走)
     + factcheck(品牌错误信息),出一张综合监测表。

纯标准库,确定性。不联网、不实时监控(刻意),采集由宿主完成。
"""

from . import sov as sovlib
from . import lostprompt as lplib
from . import factcheck as fclib


_SAMPLE_PER = 5     # 每问句每平台重复采样次数
_SAMPLE_PLATFORMS = 5  # 建议覆盖平台数


def collection_kit(brand, engines, prompt_rows, competitors=None):
    """产出采集工具包。prompt_rows 来自 prompts.generate(可空)。"""
    prompts = []
    for r in (prompt_rows or []):
        # prompts.generate 的行结构含 'prompt' 字段
        p = r.get("prompt") if isinstance(r, dict) else str(r)
        if p:
            prompts.append(p)
    engines_specified = bool(engines)
    # 未指定引擎时,按协议建议的平台数估算,别用 1 引擎下限自相矛盾
    basis = len(engines) if engines_specified else _SAMPLE_PLATFORMS
    total_samples = len(prompts) * basis * _SAMPLE_PER if prompts else None
    return {
        "engines_specified": engines_specified,
        "estimate_basis": basis,
        "brand": brand,
        "engines": list(engines or []),
        "competitors": list(competitors or []),
        "protocol": ("监测=概率:每个 prompt 在每个目标引擎用同样方式重复问 %d 次,覆盖约 %d 个平台,"
                     "取均值=品牌被推荐概率。采样越多越稳,报采样置信度。"
                     % (_SAMPLE_PER, _SAMPLE_PLATFORMS)),
        "sample_per_prompt_engine": _SAMPLE_PER,
        "estimated_total_samples": total_samples,
        "prompts_to_ask": prompts,
        "records_schema": {
            "type": "array of records",
            "record": {"prompt": "你问的问句", "engine": "豆包/deepseek/chatgpt...",
                       "answer": "AI 的完整回答原文", "turn": "可选,多轮对话第几轮(整数)"},
            "example": [{"prompt": "公众号排版工具哪个好", "engine": "豆包",
                         "answer": "推荐 A、B、C ...(粘贴完整回答)"}],
        },
        "feed_back": [
            "geo_cli sov --input records.json --brand %s%s   # 看自己占位/sentiment/earned-owned" % (
                brand or "你的品牌", (" --brand-domain 你的域名" if brand else "")),
            "geo_cli lostprompt --input records.json --brand %s --competitor 竞品   # 看哪些问句被竞品夺走" % (
                brand or "你的品牌"),
            "geo_cli factcheck --input records.json --brand %s --facts facts.json   # 看 AI 有没有说错你" % (
                brand or "你的品牌"),
        ],
        "note": "宿主 agent 或人工去目标引擎逐条问、把回答原样粘进 records.json,再喂上面三条命令闭环。"
                "绝不编造 AI 回答,采集到什么记什么。",
    }


def render_kit(kit):
    o = []
    o.append("**采样协议:** " + kit["protocol"])
    if kit["estimated_total_samples"]:
        basis_label = ("%d 引擎" % len(kit["engines"])) if kit["engines_specified"] \
            else "建议 %d 平台(未指定引擎,按协议估算)" % kit["estimate_basis"]
        o.append("建议采集工作量(目标值,尚未采集):%d 个 prompt × %s × %d 次 ≈ 需采集约 %d 次。" % (
            len(kit["prompts_to_ask"]), basis_label,
            kit["sample_per_prompt_engine"], kit["estimated_total_samples"]))
    if kit["prompts_to_ask"]:
        o.append("")
        o.append("**要去问的 prompt(节选前 10):**")
        for p in kit["prompts_to_ask"][:10]:
            o.append("- " + p)
    o.append("")
    o.append("**records.json 格式:** `[{\"prompt\":..., \"engine\":..., \"answer\":...}]`(answer 粘 AI 完整回答原文)")
    o.append("")
    o.append("**采集回来喂这三条命令闭环:**")
    for f in kit["feed_back"]:
        o.append("- `%s`" % f)
    o.append("")
    o.append("> " + kit["note"])
    return "\n".join(o)


def measure_all(records, brand, competitors=None, facts=None, aliases=None,
                brand_domain=None):
    """一键把 records 同时喂 sov + lostprompt + factcheck,出综合监测表。"""
    out = {"brand": brand, "record_count": len(records)}
    out["sov"] = sovlib.analyze(records, brand, competitors=competitors,
                                aliases=aliases, brand_domain=brand_domain)
    if competitors:
        out["lostprompt"] = lplib.analyze(records, brand, competitors, aliases=aliases)
    else:
        out["lostprompt"] = None
    if facts:
        out["factcheck"] = fclib.check(records, brand, facts, aliases=aliases)
    else:
        out["factcheck"] = None
    return out


def render_measure(m):
    o = ["# 综合监测报告:%s" % m["brand"], ""]
    o.append("采集记录数:%d" % m["record_count"])
    sov = m["sov"]
    cov = sov.get("coverage") or {}
    o.append("")
    o.append("## 占位(SoV)")
    if cov.get("rate") is not None:
        o.append("- 问句覆盖率:**%s%%**(%d/%d 个问句-引擎组至少提到你一次;广度指标,"
                 "单问句稳定被推荐度看 sampling 的采样置信度)" % (
                     cov["rate"], cov.get("hit", 0), cov.get("total", 0)))
    msov = sov.get("mention_sov") or {}
    if msov:
        share = "、".join("%s %s%%" % (b, p) for b, p in
                         sorted(msov.items(), key=lambda kv: -kv[1])[:4])
        o.append("- 声量份额(vs 竞品):%s" % share)
    o.append("- 竞争档位:%s" % sov.get("competitive_tier", "未知"))
    sent = sov.get("mention_sentiment")
    if sent:
        o.append("- 被引情绪:正 %d / 中 %d / 负 %d" % (
            sent["positive"]["count"], sent.get("neutral", {}).get("count", 0),
            sent["negative"]["count"]))
    if m["lostprompt"]:
        lp = m["lostprompt"]
        o.append("")
        o.append("## 竞品夺走(lostprompt)")
        o.append("- 输掉 %d 个 prompt,赢 %d 个" % (lp["lost_count"], lp["won_count"]))
        for lost in lp.get("lost_prompts", [])[:5]:
            o.append("  - 输:%s" % lost.get("prompt", ""))
    if m["factcheck"]:
        fc = m["factcheck"]
        o.append("")
        o.append("## 品牌错误信息(factcheck)")
        o.append("- 冲突 %d 处" % fc["conflict_count"])
        for c in fc.get("conflicts", [])[:5]:
            o.append("  - AI 说错「%s」,真相「%s」" % (c.get("attribute", ""), c.get("truth", "")))
    o.append("")
    o.append("> 优化 GEO 本质是把提及率(概率)从 A 提到 B。按 lostprompt 输掉的问句回填信源,再采样复测。")
    return "\n".join(o)
