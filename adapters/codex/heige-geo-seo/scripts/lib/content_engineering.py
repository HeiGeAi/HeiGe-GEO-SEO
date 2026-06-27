"""内容工程 11 要素加权评分(来源:WaytoAGI《GEO 内容工程》公开课方法论)。

姚金刚团队从"爬 1 万条 AI 结果分析高频引用特征 + 自爬国内平台引用"研究中,
拆出 11 个要素、9 个分层,每个带可计算公式和规则权重,证据引用层合计 43% 最重要。
本模块按这套权重和公式给单篇内容打分,补全 6 维评分卡偏粗的内容质量维度,
直接回答"为什么这篇会被 AI 反复引用"。确定性 + 启发式,纯标准库。

诚实边界:
- 规则权重来自单一应用型研究(有主观性),按方向性口径用,可在 _ELEMENTS 调。
- 11 项规则权重相加为 98(公开课原始口径),展示总分按 98 归一化到 0-100。
- 语义类要素(语义密度/需求匹配)无 query 上下文时低置信,仅作参考,不进"最该先补"。
- 统计数据要素只数真数字密度作信号,不验真伪;高分不代表数据可信,终审必须人工核源,
  素材不足绝不编造引语/统计/来源。
"""

import re


# (key, 层, 要素, 权重%, 计算说明)
_ELEMENTS = [
    ("authority_quote", "证据引用层", "权威原文引语", 16, "权威引语句数÷核心结论句数×来源可信度"),
    ("statistics", "证据引用层", "统计数据", 14, "含数据的核心段落数÷核心段落数×数据口径完整度"),
    ("citability", "证据引用层", "可引用性/可信来源", 13, "带出处的关键事实数÷全部关键事实数×来源质量"),
    ("structure", "结构理解层", "结构规范性", 12, "标题层级×0.3+摘要结论×0.2+列表表格×0.2+FAQ步骤×0.3"),
    ("fluency", "表达理解层", "表达流畅度", 10, "逻辑连贯度×0.4+段落均衡×0.3+句子清晰度×0.3"),
    ("semantic", "语义匹配层", "语义密度/需求匹配", 8, "主题实体覆盖率×0.4+用户问题覆盖率×0.4+自然分布×0.2"),
    ("authority_signal", "信任权威层", "权威信号", 7, "作者/机构资质×0.3+方法标准×0.3+案例经验×0.2+限制说明×0.2"),
    ("terminology", "专业表达层", "专业术语", 6, "领域术语密度×0.4+定义完整度×0.3+术语解释×0.3"),
    ("robustness", "稳健性层", "鲁棒性/多源支撑", 5, "有证据段落占比×0.3+多源校验×0.3+反例边界×0.2+更新日期×0.1"),
    ("cross_domain", "跨域连接层", "跨域贡献", 4, "相关领域连接×0.4+应用场景覆盖×0.3+案例迁移性×0.3"),
    ("readability", "可读性层", "易懂表达", 3, "句长适中×0.4+段落短句化×0.3+术语翻译×0.3"),
]
_RAW_TOTAL = sum(w for _, _, _, w, _ in _ELEMENTS)  # 98:公开课原始口径

# 无 query 时低置信的要素,不进"最该先补"排序
_LOW_CONFIDENCE = {"semantic"}

# 真引语:成对引号包裹的长句,或"据 X 报告/研究/显示/指出/称"(不含'数据',太常见)
_QUOTE_MARK = re.compile(r"[“「『][^”」』]{6,}?[”」』]"
                         r"|据[^,，。；\s]{2,16}?(?:报告|研究|白皮书|论文|显示|指出|表示|称)")
# 强出处词(给可引用性真实信号下限)
_STRONG_SRC = re.compile(r"来源|出处|引自|引用自|据.{0,12}?(?:报告|研究|白皮书|论文)|参考文献")
# 一般出处词(弱信号,去掉单字'据'避免命中 数据/根据/占据)
_SRC_HINT = re.compile(r"来源|出处|引自|参考|根据|依据|链接|http", re.IGNORECASE)
_NUM = re.compile(r"\d+(?:[.,]\d+)?%?")
# 日期:覆盖 -、/、年月 三种分隔符(非捕获,re.sub 不残留)
_DATE_ANY = re.compile(r"\d{4}[-/年]\d{1,2}(?:[-/月]\d{1,2})?日?")
# 版本号:带 v 的两段及以上,或裸三段及以上(裸两段如 87.3 当小数统计,不剔)
_VERSION = re.compile(r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+\.\d+\b", re.IGNORECASE)
_FAQ = re.compile(r"(常见问题|FAQ|Q[:：&]|问[:：].{0,30}答[:：]|什么是|如何|怎么|为什么)", re.IGNORECASE)
_SUMMARY = re.compile(r"(摘要|概要|导语|引言|TL;?DR|核心(结论|要点)|一句话|本文(将|介绍|讲|带你))", re.IGNORECASE)
_AUTH_SIGNAL = re.compile(r"(院士|教授|博士|首席|CTO|CEO|创始人|上市公司|中国科学院|工程院|\d+\s*年(?:经验|从业))")
_LIMIT = re.compile(r"(局限|限制|注意|前提|适用范围|不适用|风险|免责)")
_DATED_NEAR = re.compile(r"(更新|修订|发布|最后更新|last\s*updated?)[^。\n]{0,12}\d{4}[-/年]\d{1,2}", re.IGNORECASE)
_MULTI_SRC = re.compile(r"(多方|多源|交叉验证|综合各|各方|不同来源|对比验证)")
# 英文实体停用词(避免缩写/虚词把语义密度刷高)
_EN_STOP = {"THE", "OUR", "AND", "FOR", "WITH", "FAQ", "CTO", "CEO", "API", "GPT",
            "BERT", "LLM", "SDK", "JSON", "YAML", "ROI", "KPI", "HTTP", "HTTPS",
            "URL", "UI", "UX", "SEO", "GEO", "CSS", "HTML", "AI", "ML", "AN", "IS", "IT"}


def _clamp(x):
    return max(0.0, min(1.0, x))


def _strip_dates(s):
    """剔除日期和明确版本号,避免把 2026/06/01、2026年6月、v2.0 当统计数字。"""
    s = _DATE_ANY.sub(" ", s)
    s = _VERSION.sub(" ", s)
    return s


def _real_number_count(doc):
    """统计真数字:剔除日期/版本号后的数字个数(同 number_count 口径,且覆盖斜杠/中文日期)。"""
    return len(_NUM.findall(_strip_dates(doc.text)))


def _score_elements(doc):
    text = doc.text
    sents = doc.sentences()
    n_sent = max(1, len(sents))
    wc = max(1, doc.word_count())
    paras = [p for p in doc.text.split("\n") if p.strip()]
    n_para = max(1, len(paras))
    headings = doc.headings
    ext = len(doc.external_links())
    s = {}

    # 权威原文引语:真引语/可信出处句占核心句比例(噪声词不计)
    quotes = len(_QUOTE_MARK.findall(text))
    s["authority_quote"] = _clamp(quotes / max(3, n_sent * 0.15))

    # 统计数据:带真数字段落占比 × 真数字密度(先 strip 日期/版本号)
    data_paras = sum(1 for p in paras if _NUM.search(_strip_dates(p)))
    nums = _real_number_count(doc)
    if nums == 0:
        s["statistics"] = 0.0
    else:
        s["statistics"] = _clamp((data_paras / n_para) * 0.6 + min(1.0, nums / (wc / 100 * 4)) * 0.4)

    # 可引用性/可信来源:出处词 + 外链;真实信号下限——无外链且无强出处词时封顶 0.4
    src_hits = len(_SRC_HINT.findall(text))
    src_score = src_hits / max(3, n_sent * 0.1) * 0.6 + min(1.0, ext / 3) * 0.4
    has_real_anchor = ext > 0 or _STRONG_SRC.search(text) is not None
    s["citability"] = _clamp(src_score) if has_real_anchor else min(0.4, _clamp(src_score))

    # 结构规范性:标题层级×0.3 + 摘要结论×0.2 + 列表表格×0.2 + FAQ×0.3
    levels = set(lv for lv, _ in headings)
    if len(levels) >= 2:
        heading_hier = 1.0
    elif headings:
        heading_hier = 0.5
    else:
        heading_hier = 0.0
    summary = 1 if _SUMMARY.search(text) else 0
    lists_tables = doc.counts["ul"] + doc.counts["ol"] + doc.counts["table"]
    faq = 1 if _FAQ.search(text) else 0
    s["structure"] = _clamp(heading_hier * 0.3 + summary * 0.2 +
                            min(1.0, lists_tables / 2) * 0.2 + faq * 0.3)

    # 表达流畅度:句长适中 + 段落均衡(无段落=无均衡,给 0 不兜底)
    avg = doc.avg_sentence_words()
    sent_ok = 1.0 if 12 <= avg <= 28 else (0.5 if 8 <= avg <= 40 else 0.0)
    plens = [len(p) for p in paras]
    balance = (1.0 - (max(plens) - min(plens)) / max(plens)) if (plens and max(plens)) else 0.0
    s["fluency"] = _clamp(sent_ok * 0.6 + _clamp(balance) * 0.4)

    # 语义密度/需求匹配:实体覆盖 + 问句覆盖(低置信,无 query 时启发式近似)
    en_ent = [w for w in re.findall(r"[A-Z][A-Za-z0-9]{1,}", text) if w.upper() not in _EN_STOP]
    cn_ent = re.findall(r"[一-鿿]{2,6}(?=(?:是|提供|支持|可以|可用于|采用|属于))", text)
    entities = len(en_ent) + len(cn_ent)
    q_cover = len(_FAQ.findall(text))
    s["semantic"] = _clamp(min(1.0, entities / max(10, wc / 50)) * 0.5 + min(1.0, q_cover / 3) * 0.5)

    # 权威信号:作者/机构资质 + 限制说明
    auth = len(_AUTH_SIGNAL.findall(text))
    limit = 1 if _LIMIT.search(text) else 0
    s["authority_signal"] = _clamp(min(1.0, auth / 2) * 0.7 + limit * 0.3)

    # 专业术语:定义块密度
    defs = len(re.findall(r"[一-鿿A-Za-z]{2,12}(?:是指|指的是|定义为|是一种|属于)", text))
    s["terminology"] = _clamp(min(1.0, defs / 3))

    # 鲁棒性/多源:多源校验 + 靠近更新语义的日期 + 外链
    multi = 1 if _MULTI_SRC.search(text) else 0
    dated = 1 if (_DATED_NEAR.search(text) or doc.time_attrs) else 0
    s["robustness"] = _clamp(multi * 0.5 + dated * 0.3 + min(1.0, ext / 3) * 0.2)

    # 跨域贡献:场景/应用词
    scenes = len(re.findall(r"(场景|应用|案例|适用于|可用于|举例)", text))
    s["cross_domain"] = _clamp(min(1.0, scenes / 4))

    # 易懂表达:句长 + 短段落
    short_para = sum(1 for p in paras if len(p) <= 120) / n_para
    s["readability"] = _clamp(sent_ok * 0.5 + short_para * 0.5)

    return s


def score(doc, market="auto"):
    """按 11 要素加权模型给单篇内容打分。展示总分按 98 归一化到 0-100;逐要素拆解。"""
    el = _score_elements(doc)
    rows = []
    raw_total = 0.0
    for key, layer, name, weight, formula in _ELEMENTS:
        v = el.get(key, 0.0)
        contrib = v * weight
        raw_total += contrib
        rows.append({
            "key": key, "layer": layer, "element": name, "weight": weight,
            "score_0_1": round(v, 2), "weighted": round(contrib, 2),
            "formula": formula,
            "low_confidence": key in _LOW_CONFIDENCE,
        })
    # 归一化到 0-100(规则权重和为 98)
    total = round(raw_total / _RAW_TOTAL * 100, 1)
    evidence_raw = round(sum(r["weighted"] for r in rows if r["layer"] == "证据引用层"), 1)
    # "最该先补":排除低置信要素,按性价比(加权/权重)升序
    rankable = [r for r in rows if not r["low_confidence"]]
    weakest = sorted(rankable, key=lambda r: r["weighted"] / max(1, r["weight"]))[:3]
    if total >= 80:
        grade = "绩优"
    elif total >= 60:
        grade = "合格"
    elif total >= 40:
        grade = "待优化"
    else:
        grade = "弱"
    return {
        "model": "content-engineering-11",
        "source": "WaytoAGI《GEO 内容工程》公开课(姚金刚)+ 爬1万条AI结果研究",
        "score": total,
        "score_scale": "0-100(规则权重和 98,已归一化)",
        "grade": grade,
        "evidence_layer_raw": evidence_raw,
        "evidence_layer_max_raw": 43,
        "evidence_layer_note": "证据引用层(权威引语+统计数据+可引用性)占规则权重 43/98≈44%,是被引用第一杠杆",
        "elements": rows,
        "weakest": [{"element": r["element"], "layer": r["layer"],
                     "weighted": r["weighted"], "weight": r["weight"],
                     "formula": r["formula"]} for r in weakest],
        "note": "规则权重来自单一应用型研究(有主观性),为方向性口径。语义密度要素无 query 时低置信、"
                "仅供参考(已排除出最该先补)。统计数据只数真数字密度作信号,不验真伪,高分不代表数据可信,"
                "终审必须人工核源,素材不足绝不编造引语/统计/来源。重点先补证据引用层"
                "(权威原文引语 16% + 统计数据 14% + 可引用性 13%)。",
    }


def render(result):
    out = ["# 内容工程 11 要素加权评分", ""]
    out.append("总分: **%s/100**(%s) | 证据引用层: %s/%s(规则权重 43/98)" % (
        result["score"], result["grade"], result["evidence_layer_raw"],
        result["evidence_layer_max_raw"]))
    out.append("> 来源: " + result["source"])
    out.append("")
    out.append("| 层 | 要素 | 权重 | 得分(0-1) | 加权 | 备注 |")
    out.append("|---|---|---|---|---|---|")
    for r in result["elements"]:
        tag = "低置信" if r["low_confidence"] else ""
        out.append("| %s | %s | %d | %.2f | %.2f | %s |" % (
            r["layer"], r["element"], r["weight"], r["score_0_1"], r["weighted"], tag))
    out.append("")
    out.append("最该先补(证据引用层优先,已排除低置信要素):")
    for w in result["weakest"]:
        out.append("- %s(%s,权重 %d,当前加权 %.1f):%s" % (
            w["element"], w["layer"], w["weight"], w["weighted"], w["formula"]))
    out.append("")
    out.append("> " + result["note"])
    return "\n".join(out)
