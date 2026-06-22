"""Share of Voice 度量 + prompt 覆盖率 + 采样置信度。

度量学 100% 离线。输入是宿主 agent / 人工跑大模型后回填的"prompt→answer"记录,
脚本算可见度,不自己联网。对齐国内口径:提及率 + SOV 声量占比 + 推荐排名 + 别名合并。

records: list of {prompt, engine, answer[, run]}
"""

import re


# 竞争位基准阈值(Mention SoV / Weighted SoV),来自竞品方法学
_TIERS = [
    ("领导者", 40, 35),
    ("Top3 挑战者", 20, 15),
    ("Top10", 10, 7),
    ("新进入者", 0, 0),
]

_URL_RE = re.compile(r"https?://([^/\s)\]]+)")


def _domain(host):
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _aliases_for(name, aliases):
    out = [name]
    if aliases and name in aliases:
        out += aliases[name]
    return out


def parse_answer(answer, brands, aliases=None):
    """返回 {brand: position}(按首次出现顺序排名,1=最先)+ 引用域名列表。"""
    first_idx = {}
    for b in brands:
        idx = None
        for alias in _aliases_for(b, aliases):
            if not alias:
                continue
            p = answer.find(alias)
            if p >= 0 and (idx is None or p < idx):
                idx = p
        if idx is not None:
            first_idx[b] = idx
    # rank by appearance order
    ranked = sorted(first_idx.items(), key=lambda kv: kv[1])
    positions = {b: i + 1 for i, (b, _) in enumerate(ranked)}
    citations = [_domain(h) for h in _URL_RE.findall(answer)]
    return {"positions": positions, "citations": citations}


def analyze(records, brand, competitors=None, aliases=None,
            brand_domain=None, competitor_domains=None):
    competitors = competitors or []
    brands = [brand] + competitors
    domains = {}
    if brand_domain:
        domains[brand] = _domain(brand_domain)
    for b, d in (competitor_domains or {}).items():
        domains[b] = _domain(d)

    # group by (prompt, engine) for sampling stability
    groups = {}
    engines = set()
    for r in records:
        eng = r.get("engine", "default")
        engines.add(eng)
        key = (r["prompt"], eng)
        groups.setdefault(key, []).append(r)

    # accumulators
    mention = {b: 0 for b in brands}          # count of answers brand appears
    weighted = {b: 0.0 for b in brands}       # sum of 1/position
    citation = {b: 0 for b in brands}
    total_citations = 0
    per_engine = {}
    coverage_hits = 0
    coverage_total = 0
    unstable = []

    for (prompt, eng), samples in groups.items():
        coverage_total += 1
        appear_counts = {b: 0 for b in brands}
        for r in samples:
            parsed = parse_answer(r.get("answer", ""), brands, aliases)
            for b, pos in parsed["positions"].items():
                mention[b] += 1
                weighted[b] += 1.0 / pos
                pe = per_engine.setdefault(eng, {"mention": {x: 0 for x in brands},
                                                 "weighted": {x: 0.0 for x in brands}})
                pe["mention"][b] += 1
                pe["weighted"][b] += 1.0 / pos
                appear_counts[b] += 1
            for dom in parsed["citations"]:
                total_citations += 1
                for b, bd in domains.items():
                    if bd and bd in dom:
                        citation[b] += 1
        # sampling stability for the tracked brand
        rate = appear_counts[brand] / len(samples) if samples else 0
        if 0 < rate < 1:
            unstable.append({"prompt": prompt, "engine": eng,
                             "appearance_rate": round(rate, 2)})
        if appear_counts[brand] > 0:
            coverage_hits += 1

    def sov(counts):
        total = sum(counts.values())
        return {b: round(counts[b] / total * 100, 1) if total else 0.0 for b in brands}

    mention_sov = sov(mention)
    weighted_total = sum(weighted.values())
    weighted_sov = {b: round(weighted[b] / weighted_total * 100, 1) if weighted_total else 0.0
                    for b in brands}
    citation_sov = ({b: round(citation[b] / total_citations * 100, 1) if total_citations else 0.0
                     for b in brands} if domains else None)

    tier = classify_tier(mention_sov[brand], weighted_sov[brand])

    engine_breakdown = {}
    for eng, pe in per_engine.items():
        engine_breakdown[eng] = sov(pe["mention"])

    return {
        "brand": brand,
        "competitors": competitors,
        "engines": sorted(engines),
        "coverage": {
            "hit": coverage_hits, "total": coverage_total,
            "rate": round(coverage_hits / coverage_total * 100, 1) if coverage_total else 0.0,
        },
        "mention_sov": mention_sov,
        "weighted_sov": weighted_sov,
        "citation_sov": citation_sov,
        "competitive_tier": tier,
        "per_engine_mention_sov": engine_breakdown,
        "sampling": {
            "unstable_prompts": unstable,
            "note": "出现率在 0~1 之间的 prompt 采样不稳定,建议每 prompt 每引擎重复 3-5 次再聚合",
        },
    }


def classify_tier(mention_sov, weighted_sov):
    for name, m_th, w_th in _TIERS:
        if mention_sov >= m_th and weighted_sov >= w_th:
            return name
    return "新进入者"
