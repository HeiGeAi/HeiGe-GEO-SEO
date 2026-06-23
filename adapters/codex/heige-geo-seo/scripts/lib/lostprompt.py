"""竞品替换分析(Lost Prompt Analysis):找竞品压制你的 prompt,定位该夺回哪些。

度量(sov)告诉你竞品声量比你高,这里回答"在哪些具体 prompt 上、被谁、怎么夺回"。
找出"竞品出现且你缺席"的 prompt 子集,按引擎聚类,标谁赢、缺口在哪。纯标准库,
采集寄生宿主 agent。
"""

from . import sov as _sov


def analyze(records, brand, competitors, aliases=None):
    """records: list of {prompt, engine, answer}。返回输的 prompt + 谁赢 + 该夺回。"""
    competitors = competitors or []
    brands = [brand] + competitors
    lost = []
    won = []
    contested = []
    # 按 (prompt, engine) 聚合,任一样本里出现即算出现
    groups = {}
    for r in records:
        key = (r.get("prompt", ""), r.get("engine", "default"))
        groups.setdefault(key, []).append(r)

    for (prompt, eng), samples in groups.items():
        brand_in = False
        comp_in = set()
        for r in samples:
            pos = _sov.parse_answer(r.get("answer", ""), brands, aliases)["positions"]
            if brand in pos:
                brand_in = True
            for c in competitors:
                if c in pos:
                    comp_in.add(c)
        row = {"prompt": prompt, "engine": eng,
               "brand_present": brand_in, "competitors_present": sorted(comp_in)}
        if comp_in and not brand_in:
            row["fix_priority"] = "high"
            row["why"] = "竞品 %s 占位,你缺席。对照该 prompt 补内容 + 铺第三方源夺回" % "、".join(sorted(comp_in))
            lost.append(row)
        elif brand_in and not comp_in:
            won.append(row)
        elif brand_in and comp_in:
            contested.append(row)

    # 按引擎聚类输的 prompt
    by_engine = {}
    for row in lost:
        by_engine.setdefault(row["engine"], []).append(row["prompt"])

    # 哪个竞品赢得最多
    winner_count = {}
    for row in lost:
        for c in row["competitors_present"]:
            winner_count[c] = winner_count.get(c, 0) + 1

    return {
        "brand": brand,
        "competitors": competitors,
        "lost_count": len(lost),
        "won_count": len(won),
        "contested_count": len(contested),
        "lost_prompts": lost,
        "lost_by_engine": by_engine,
        "top_displacers": sorted(winner_count.items(), key=lambda kv: -kv[1]),
        "note": "lost = 竞品出现且你缺席,优先夺回;接 instruction 出针对性改写,接 publishing 铺第三方源。",
    }


def render(result):
    out = ["# 竞品替换分析(Lost Prompt): %s" % result["brand"], ""]
    out.append("输 %d / 赢 %d / 争夺中 %d" % (
        result["lost_count"], result["won_count"], result["contested_count"]))
    if result["top_displacers"]:
        out.append("主要压制者: " + "、".join("%s(%d)" % (c, n) for c, n in result["top_displacers"]))
    out.append("")
    out.append("| 输的 prompt | 引擎 | 被谁占位 |")
    out.append("|---|---|---|")
    for row in result["lost_prompts"]:
        out.append("| %s | %s | %s |" % (
            row["prompt"], row["engine"], "、".join(row["competitors_present"])))
    return "\n".join(out)
