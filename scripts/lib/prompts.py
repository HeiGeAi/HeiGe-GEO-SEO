"""Buyer prompt 集生成器(GEO 版关键词覆盖)。

生成"用户会怎么问 AI"的意图问句集,按漏斗阶段 × 意图类型 × 品牌/非品牌分层。
脚本只生成 + 后续解析,真去问大模型交给宿主 agent 或人工(零联网依赖)。
方法学锚点(竞品实证):规模 100-200/引擎、每 prompt 重复采样 3-5 次、非品牌词优先于品牌词。
"""

import csv
import io
import json


# (模板, 意图, 漏斗阶段, 品牌类型)  占位符: {category}{brand}{competitor}{problem}{persona}{geo}{usecase}
_TEMPLATES_ZH = [
    ("{category}是什么", "informational", "awareness", "non-brand"),
    ("{category}怎么选", "informational", "awareness", "non-brand"),
    ("最好的{category}有哪些", "best-top", "awareness", "non-brand"),
    ("推荐几个好用的{category}", "best-top", "evaluation", "non-brand"),
    ("{problem}怎么解决", "problem-aware", "awareness", "non-brand"),
    ("{category}能解决{problem}吗", "solution-aware", "evaluation", "non-brand"),
    ("{persona}适合用什么{category}", "use-case", "evaluation", "non-brand"),
    ("{usecase}用哪个{category}比较好", "use-case", "evaluation", "non-brand"),
    ("{brand}怎么样", "brand-eval", "evaluation", "brand"),
    ("{brand}和{competitor}哪个好", "comparison", "evaluation", "brand"),
    ("{category}里{brand}和{competitor}怎么选", "comparison", "evaluation", "brand"),
    ("{brand}多少钱", "buyer-stage", "conversion", "brand"),
    ("{brand}值得买吗", "buyer-stage", "conversion", "brand"),
    ("{geo}有哪些{category}", "local", "evaluation", "non-brand"),
    ("{brand}怎么用", "support", "post-purchase", "brand"),
]

_TEMPLATES_EN = [
    ("what is {category}", "informational", "awareness", "non-brand"),
    ("how to choose a {category}", "informational", "awareness", "non-brand"),
    ("best {category} tools", "best-top", "awareness", "non-brand"),
    ("top {category} recommendations", "best-top", "evaluation", "non-brand"),
    ("how to solve {problem}", "problem-aware", "awareness", "non-brand"),
    ("can {category} solve {problem}", "solution-aware", "evaluation", "non-brand"),
    ("best {category} for {persona}", "use-case", "evaluation", "non-brand"),
    ("which {category} is best for {usecase}", "use-case", "evaluation", "non-brand"),
    ("is {brand} any good", "brand-eval", "evaluation", "brand"),
    ("{brand} vs {competitor}", "comparison", "evaluation", "brand"),
    ("{brand} or {competitor} for {category}", "comparison", "evaluation", "brand"),
    ("how much does {brand} cost", "buyer-stage", "conversion", "brand"),
    ("is {brand} worth it", "buyer-stage", "conversion", "brand"),
    ("{category} in {geo}", "local", "evaluation", "non-brand"),
    ("how to use {brand}", "support", "post-purchase", "brand"),
]


def _fill(tmpl, brand, category, competitor, problem, persona, geo, usecase):
    try:
        return tmpl.format(brand=brand or "", category=category or "",
                           competitor=competitor or "", problem=problem or "",
                           persona=persona or "", geo=geo or "", usecase=usecase or "")
    except KeyError:
        return None


def _clean(values):
    return [v for v in (values or []) if v and str(v).strip()]


def generate(brand, category, competitors=None, problems=None, personas=None,
             geographies=None, usecases=None, lang="zh", limit=None):
    """生成 buyer prompt 集。非品牌词优先(放前面)。
    缺值的占位符模板直接跳过,不产残句。"""
    competitors = _clean(competitors)
    problems = _clean(problems)
    personas = _clean(personas)
    geographies = _clean(geographies)
    usecases = _clean(usecases)
    tmpls = _TEMPLATES_ZH if lang == "zh" else _TEMPLATES_EN

    rows = []
    seen = set()

    def add(text, intent, funnel, btype):
        if not text or "{" in text or "}" in text:
            return
        text = text.strip()
        if text in seen:
            return
        seen.add(text)
        rows.append({"prompt": text, "intent": intent, "funnel": funnel,
                     "brand_type": btype, "lang": lang})

    _slot = {"{competitor}": competitors, "{problem}": problems,
             "{persona}": personas, "{geo}": geographies, "{usecase}": usecases}

    for tmpl, intent, funnel, btype in tmpls:
        # skip a template if it uses a placeholder we have no values for
        if any(ph in tmpl and not vals for ph, vals in _slot.items()):
            continue
        comp_list = competitors if "{competitor}" in tmpl else [None]
        prob_list = problems if "{problem}" in tmpl else [None]
        pers_list = personas if "{persona}" in tmpl else [None]
        geo_list = geographies if "{geo}" in tmpl else [None]
        uc_list = usecases if "{usecase}" in tmpl else [None]
        for c in comp_list:
            for pr in prob_list:
                for pe in pers_list:
                    for g in geo_list:
                        for uc in uc_list:
                            text = _fill(tmpl, brand, category, c, pr, pe, g, uc)
                            add(text, intent, funnel, btype)

    # non-brand first (higher info value), then brand
    rows.sort(key=lambda r: 0 if r["brand_type"] == "non-brand" else 1)
    for i, r in enumerate(rows, 1):
        r["id"] = "p%03d" % i
        r["samples_recommended"] = 3
    if limit:
        rows = rows[:limit]
    return rows


def to_json(rows, meta=None):
    return json.dumps({"meta": meta or {}, "count": len(rows), "prompts": rows},
                      ensure_ascii=False, indent=2) + "\n"


def to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "prompt", "intent", "funnel", "brand_type", "lang", "samples_recommended"])
    for r in rows:
        w.writerow([r["id"], r["prompt"], r["intent"], r["funnel"],
                    r["brand_type"], r["lang"], r["samples_recommended"]])
    return buf.getvalue()
