"""品牌错误信息纠正:确定性比对 AI 回答里关于品牌的事实陈述,标出冲突。

被 AI 引用了但说错了(说你停产、价格错、把你和竞品功能搞混),错误会被反复复述、
沉淀进训练语料,是 GEO 实战的高优先级危机。这里只做确定性检测:host agent / 人工
提供品牌真相(facts),工具扫 AI 回答里的"错误说法"并给出修复指向。纯标准库。

facts: list of {"attribute": 属性名, "truth": 正确值, "wrong": [错误说法...]}
records: list of {prompt, engine, answer}
"""


def _aliases(brand, aliases):
    out = [brand]
    if aliases and brand in aliases:
        out += aliases[brand]
    return [a for a in out if a]


def check(records, brand, facts, aliases=None):
    """扫描每条回答,找提到品牌且出现"错误说法"的,标为待纠正。"""
    brand_names = _aliases(brand, aliases)
    findings = []
    window = 60  # 错误说法须落在品牌名邻近窗口内,避免把竞品的"停产"算到你头上
    for r in records:
        ans = r.get("answer", "")
        # 品牌出现的所有区间
        brand_spans = []
        for n in brand_names:
            start = 0
            while True:
                i = ans.find(n, start)
                if i < 0:
                    break
                brand_spans.append((i, i + len(n)))
                start = i + 1
        if not brand_spans:
            continue
        for f in facts:
            for wrong in f.get("wrong", []):
                if not wrong:
                    continue
                wi = ans.find(wrong)
                near = False
                while wi >= 0:
                    we = wi + len(wrong)
                    if any(not (we < bs - window or wi > be + window)
                           for bs, be in brand_spans):
                        near = True
                        break
                    wi = ans.find(wrong, wi + 1)
                if near:
                    findings.append({
                        "prompt": r.get("prompt"),
                        "engine": r.get("engine", "default"),
                        "attribute": f.get("attribute", ""),
                        "ai_said": wrong,
                        "truth": f.get("truth", ""),
                        "fix": "AI 说'%s',实为'%s'。修法:在官网/百度百科/Wikipedia 等"
                               "权威实体页强化正确事实(%s),补 Organization/sameAs 让 AI 能溯源纠偏"
                               % (wrong, f.get("truth", ""), f.get("attribute", "")),
                    })
    return {
        "brand": brand,
        "records_checked": len(records),
        "conflicts": findings,
        "conflict_count": len(findings),
        "verdict": "有错误信息待纠正" if findings else "未检出已知错误信息",
        "note": "只检 facts 里声明的已知错误说法;facts 由你提供真相,工具不臆断。"
                "纠错根因多在实体层(官网事实锚点/百科词条过时/sameAs 缺失)。",
    }


def render(result):
    out = ["# 品牌错误信息检查: %s" % result["brand"], ""]
    out.append("裁决: %s(查了 %d 条回答,%d 处冲突)" % (
        result["verdict"], result["records_checked"], result["conflict_count"]))
    out.append("")
    for c in result["conflicts"]:
        out.append("## [%s] %s" % (c["engine"], c["attribute"]))
        out.append("- prompt: %s" % c["prompt"])
        out.append("- AI 说: **%s** | 实为: **%s**" % (c["ai_said"], c["truth"]))
        out.append("- 修复: %s" % c["fix"])
        out.append("")
    return "\n".join(out)
