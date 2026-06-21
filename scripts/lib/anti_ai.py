"""反 AI 味约束库。

把"人机感"做成显式约束子句,挂在每条改写指令尾部,而不是黑盒 humanizer。
约束规则源自 HeiGe 写作硬规则,也可当检测器扫描已有文本里的 AI 味。
纯标准库,确定性。
"""

import re


# 否定对比句式(AI 腔重灾区):不是X而是Y / 与其说X不如说Y / 不只是X而是Y
_NEG_CONTRAST = [
    re.compile(r"不是.{1,40}?而是"),
    re.compile(r"与其说.{1,40}?不如说"),
    re.compile(r"不只是.{1,40}?而是"),
    re.compile(r"不仅仅是.{1,40}?而是"),
]

# hedge / 模板化过渡 / 营销词
_HEDGE = ["在某种程度上", "可以说", "总的来说", "众所周知", "不言而喻",
          "值得注意的是", "毋庸置疑", "显而易见"]
_TEMPLATE_TRANSITION = ["首先", "其次", "再者", "综上所述", "总而言之", "总之",
                        "由此可见", "换句话说"]
_MARKETING = ["赋能", "生态", "惊喜", "颠覆", "革命性", "无缝", "闭环", "抓手",
              "护城河", "降维打击"]
_DASH = ["——", "—", "--"]


# 约束子句(挂在改写指令尾部)
CONSTRAINTS_ZH = [
    "句长做 burstiness 扰动:长短句交替,别让句子一样长",
    "禁用否定对比句式(不是X而是Y / 与其说X不如说Y / 不只是X而是Y),全改正面直述",
    "禁用 hedge 措辞(在某种程度上/可以说/众所周知)和模板化过渡(首先/其次/综上所述)",
    "禁用营销词(赋能/生态/惊喜/颠覆/闭环)",
    "禁用破折号(——/—/--),改用逗号或句号",
    "结论先行,先给判断和动作,再补依据",
    "用'你'不用'您',口语化,用数据和逻辑说话不堆形容词",
]

CONSTRAINTS_EN = [
    "Vary sentence length (burstiness): alternate short and long sentences",
    "No hedging or template transitions (firstly, in conclusion, it is worth noting)",
    "No marketing fluff; lead with the judgment, then the evidence",
    "Plain, concrete, data-driven; avoid generic AI phrasing",
]


def constraints(lang="zh"):
    return list(CONSTRAINTS_ZH if lang == "zh" else CONSTRAINTS_EN)


def constraint_clause(lang="zh"):
    """One-line clause to append to a rewrite instruction."""
    return "反AI味约束:" + ";".join(constraints(lang)) if lang == "zh" else \
        "Anti-AI constraints: " + "; ".join(constraints(lang))


def scan(text):
    """Detect AI-tone violations in text. Returns list of findings."""
    findings = []
    for pat in _NEG_CONTRAST:
        for m in pat.finditer(text):
            findings.append({"type": "否定对比句式", "match": m.group(0)})
    for w in _HEDGE:
        if w in text:
            findings.append({"type": "hedge措辞", "match": w})
    for w in _TEMPLATE_TRANSITION:
        if w in text:
            findings.append({"type": "模板化过渡", "match": w})
    for w in _MARKETING:
        if w in text:
            findings.append({"type": "营销词", "match": w})
    for d in _DASH:
        if d in text:
            findings.append({"type": "破折号", "match": d})
            break
    return findings


def score(text):
    """0-100 cleanliness score (100 = no AI-tone violations detected)."""
    n = len(scan(text))
    return max(0, 100 - n * 8)
