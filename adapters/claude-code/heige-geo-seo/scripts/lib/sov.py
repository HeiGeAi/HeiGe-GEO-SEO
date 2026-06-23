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

# 被引语境情感词典(确定性):正面 = 被推荐,负面 = 被劝退
# "不X" 类否定由否定前缀检测处理,_NEG_WORDS 只放本身就负的词
_POS_WORDS = ("推荐", "首选", "最佳", "最好", "领先", "优秀", "值得", "好用",
              "可靠", "best", "top", "recommend", "leading",
              "excellent", "great", "reliable", "preferred")
_NEG_WORDS = ("避免", "别用", "争议", "问题", "缺点", "弱", "风险", "投诉",
              "崩", "慎用", "avoid", "issue", "problem", "downside",
              "poor", "weak", "risk", "controversy")
_NEG_PREFIX = ("不", "没", "无", "别", "勿", "未", "莫", "非", "算不上", "称不上")


def _count_sentiment(win):
    """窗口内数正负面信号,正面词被否定前缀修饰则翻转为负面。"""
    text = win.lower()
    neg = sum(text.count(w.lower()) for w in _NEG_WORDS)
    pos = 0
    for w in _POS_WORDS:
        wl = w.lower()
        start = 0
        while True:
            i = text.find(wl, start)
            if i < 0:
                break
            pre = text[max(0, i - 3):i]
            if any(n in pre for n in _NEG_PREFIX):
                neg += 1
            else:
                pos += 1
            start = i + len(wl)
    return pos, neg


def _sentiment_window(answer, lo, hi):
    """在 [lo, hi) 窗口(已按相邻品牌截断,避免跨品牌污染)内判情感。"""
    pos, neg = _count_sentiment(answer[lo:hi])
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _domain(host):
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_match(target, host):
    """精确归属:host 等于 target 或是其子域,防钓鱼域 acme.com.evil.com 误判。"""
    if not target:
        return False
    return host == target or host.endswith("." + target)


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
    # 窗口按相邻品牌位置截断,避免把竞品的情感词算到本品牌头上
    span = 40
    idx_sorted = sorted(first_idx.values())
    sentiment = {}
    for b, idx in first_idx.items():
        prevs = [x for x in idx_sorted if x < idx]
        nexts = [x for x in idx_sorted if x > idx]
        lo = max(idx - span, (prevs[-1] + 1) if prevs else 0)
        hi = min(idx + span, nexts[0] if nexts else len(answer))
        sentiment[b] = _sentiment_window(answer, lo, hi)
    return {"positions": positions, "citations": citations, "sentiment": sentiment}


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
        key = (r.get("prompt", ""), eng)
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
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    owned_cit = 0
    earned_cit = 0
    brand_dom = domains.get(brand)

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
                if b == brand:
                    sentiment_counts[parsed["sentiment"].get(b, "neutral")] += 1
            for dom in parsed["citations"]:
                total_citations += 1
                if brand_dom and _host_match(brand_dom, dom):
                    owned_cit += 1
                else:
                    earned_cit += 1
                for b, bd in domains.items():
                    if _host_match(bd, dom):
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

    # 多轮对话(仅当记录带 turn 字段):
    #   by_turn = 分轮命中率(每轮独立);turn_retention = 真留存(同一对话首轮命中后续是否仍在)
    has_turn = any("turn" in r for r in records)
    by_turn = None
    turn_retention = None
    if has_turn:
        tg = {}
        conv = {}  # (prompt, engine) -> {turn: present}
        for r in records:
            t = r.get("turn", 1)
            present = brand in parse_answer(r.get("answer", ""), brands, aliases)["positions"]
            slot = tg.setdefault(t, [0, 0])
            slot[1] += 1
            if present:
                slot[0] += 1
            conv.setdefault((r.get("prompt", ""), r.get("engine", "default")), {})[t] = present
        by_turn = {str(t): {"hit": h, "total": n,
                            "rate": round(h / n * 100, 1) if n else 0.0}
                   for t, (h, n) in sorted(tg.items())}
        base = kept = 0
        for turns in conv.values():
            if not turns:
                continue
            first_t = min(turns)
            if turns[first_t]:
                base += 1
                if any(p for t, p in turns.items() if t > first_t):
                    kept += 1
        turn_retention = {
            "first_turn_present": base, "retained_later": kept,
            "retention_rate": round(kept / base * 100, 1) if base else None,
            "note": "首轮命中的对话里,后续轮仍提到你的比例。被追问后翻盘=低留存。",
        }

    sent_total = sum(sentiment_counts.values())
    mention_sentiment = {
        k: {"count": v, "pct": round(v / sent_total * 100, 1) if sent_total else 0.0}
        for k, v in sentiment_counts.items()}

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
        "citation_owned_earned": {
            "owned": owned_cit, "earned": earned_cit,
            "earned_pct": round(earned_cit / total_citations * 100, 1) if total_citations else 0.0,
            "note": "earned(第三方源)占比越高越抗波动;owned(自有域名)刷引用抗波动差(82-94%引用来自earned media)",
        } if brand_dom else None,
        "mention_sentiment": mention_sentiment,
        "by_turn": by_turn,
        "turn_retention": turn_retention,
        "competitive_tier": tier,
        "per_engine_mention_sov": engine_breakdown,
        "sampling": {
            "unstable_prompts": unstable,
            "note": "出现率在 0~1 之间的 prompt 采样不稳定,建议每 prompt 每引擎重复 3-5 次再聚合;turn 字段区分对话轮次(run 管抖动,turn 管对话演进)",
        },
    }


def classify_tier(mention_sov, weighted_sov):
    for name, m_th, w_th in _TIERS:
        if mention_sov >= m_th and weighted_sov >= w_th:
            return name
    return "新进入者"
