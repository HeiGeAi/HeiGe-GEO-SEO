"""GEO citability score card: 6 dimensions / 22 checks, max 100.

Deterministic. Same input -> same output. Score derived only from the
HTML document plus optional robots.txt / llms.txt text. Never fabricates:
checks whose inputs are missing are reported as `unknown` and excluded
from the denominator (page mode), so a strong page still scores well
without site-level files.

See source/methodology/scoring-card.md for the rationale.
"""

import json
import math
import re


CN_BOTS_NOTE = "国内站:不屏蔽 Baiduspider/Sogou web spider/bingbot"


# --------------------------------------------------------------------------
# robots.txt parsing
# --------------------------------------------------------------------------
def parse_robots(text):
    """Return dict: ua(lower) -> {'disallow': [paths], 'allow': [paths]}
    plus 'sitemaps': [...]. Groups stacked User-agent lines together."""
    groups = {}
    sitemaps = []
    current = []
    pending_new_group = True
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        field, value = line.split(":", 1)
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if not pending_new_group:
                current = []
            ua = value.lower()
            groups.setdefault(ua, {"disallow": [], "allow": []})
            current.append(ua)
            pending_new_group = True
        elif field in ("disallow", "allow"):
            pending_new_group = False
            for ua in current or ["*"]:
                groups.setdefault(ua, {"disallow": [], "allow": []})
                groups[ua][field].append(value)
        elif field == "sitemap":
            sitemaps.append(value)
    return {"groups": groups, "sitemaps": sitemaps}


def _ua_allowed(robots, ua):
    """True if `ua` (or the wildcard fallback) is not fully blocked."""
    groups = robots["groups"]
    key = ua.lower()
    grp = groups.get(key)
    if grp is None:
        grp = groups.get("*")
    if grp is None:
        return True  # no rule at all -> allowed by default
    # fully blocked if Disallow: / and no overriding Allow: /
    blocked = any(d.strip() == "/" for d in grp["disallow"])
    if blocked and any(a.strip() == "/" for a in grp["allow"]):
        return True
    return not blocked


# --------------------------------------------------------------------------
# JSON-LD extraction
# --------------------------------------------------------------------------
def _collect_types(node, out):
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            out.add(t)
        elif isinstance(t, list):
            for x in t:
                if isinstance(x, str):
                    out.add(x)
        for v in node.values():
            _collect_types(v, out)
    elif isinstance(node, list):
        for x in node:
            _collect_types(x, out)


def _find_nodes(node, type_name, out):
    if isinstance(node, dict):
        t = node.get("@type")
        if t == type_name or (isinstance(t, list) and type_name in t):
            out.append(node)
        for v in node.values():
            _find_nodes(v, type_name, out)
    elif isinstance(node, list):
        for x in node:
            _find_nodes(x, type_name, out)


def analyze_jsonld(blocks):
    parsed = []
    valid = True
    has_error = False
    for raw in blocks:
        try:
            parsed.append(json.loads(raw))
        except Exception:
            valid = False
            has_error = True
    types = set()
    for p in parsed:
        _collect_types(p, types)
    return {"parsed": parsed, "types": types, "all_valid": valid and bool(blocks),
            "has_error": has_error, "block_count": len(blocks)}


def _has_sameas(parsed):
    def walk(n):
        if isinstance(n, dict):
            if "sameAs" in n and n["sameAs"]:
                return True
            return any(walk(v) for v in n.values())
        if isinstance(n, list):
            return any(walk(x) for x in n)
        return False
    return any(walk(p) for p in parsed)


def _max_property_count(parsed):
    best = 0
    def walk(n):
        nonlocal best
        if isinstance(n, dict):
            keys = [k for k in n.keys() if not k.startswith("@")]
            best = max(best, len(keys))
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for x in n:
                walk(x)
    for p in parsed:
        walk(p)
    return best


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
_QA_PATTERNS = re.compile(
    r"(是什么|什么是|如何|怎么|怎样|为什么|区别|How to|What is|Why|\?|？)",
    re.IGNORECASE)
_COPULA = re.compile(r"(是|为|有|包括|指的是|属于|\bis\b|\bare\b|\bhas\b|\bhave\b|\bmeans\b)",
                     re.IGNORECASE)
_KG_HOSTS = ("wikipedia.org", "wikidata.org", "linkedin.com", "crunchbase.com")


def _status(earned, weight):
    if earned >= weight - 1e-9:
        return "pass"
    if earned <= 1e-9:
        return "fail"
    return "partial"


def _chk(cid, name, weight, earned, note=""):
    earned = max(0.0, min(float(weight), float(earned)))
    return {"id": cid, "name": name, "weight": weight,
            "earned": round(earned, 2), "status": _status(earned, weight),
            "note": note}


# --------------------------------------------------------------------------
# dimensions
# --------------------------------------------------------------------------
def _dim_A(robots, market):
    checks = []
    if market == "cn":
        checks.append(_chk("A1", "Baiduspider 准入", 5,
                           5 if _ua_allowed(robots, "baiduspider") else 0, CN_BOTS_NOTE))
        checks.append(_chk("A2", "bingbot 准入", 5,
                           5 if _ua_allowed(robots, "bingbot") else 0))
        checks.append(_chk("A3", "Sogou web spider 准入", 4,
                           4 if _ua_allowed(robots, "sogou web spider") else 0))
    else:
        ok_oai = _ua_allowed(robots, "oai-searchbot")
        ok_claude = _ua_allowed(robots, "claude-searchbot") or _ua_allowed(robots, "claudebot")
        ok_pplx = _ua_allowed(robots, "perplexitybot")
        checks.append(_chk("A1", "OpenAI 检索类(OAI-SearchBot)准入", 5, 5 if ok_oai else 0))
        checks.append(_chk("A2", "Anthropic 检索类(Claude-SearchBot)准入", 5, 5 if ok_claude else 0))
        checks.append(_chk("A3", "PerplexityBot 准入", 4, 4 if ok_pplx else 0))
    star = robots["groups"].get("*")
    fully_closed = bool(star) and any(d.strip() == "/" for d in star["disallow"])
    checks.append(_chk("A4", "无站点级全封锁(WAF 需另测)", 4, 0 if fully_closed else 4))
    return {"key": "A", "name": "AI 爬虫准入", "weight": 18, "checks": checks}


def _dim_B(robots, llms, llms_full, ai_txt):
    checks = []
    if llms is not None:
        has_h1 = bool(re.search(r"^#\s+\S", llms, re.MULTILINE))
        has_quote = bool(re.search(r"^>\s+\S", llms, re.MULTILINE))
        has_link = bool(re.search(r"^\s*[-*]\s*\[.+?\]\(.+?\)", llms, re.MULTILINE))
        earned = (4 if has_h1 else 0) + (2 if has_link else 0) + (2 if has_quote else 0)
        note = "缺 H1/链接/摘要会扣分" if earned < 8 else ""
        checks.append(_chk("B1", "llms.txt 存在且结构合格", 8, earned, note))
    else:
        checks.append(_chk("B1", "llms.txt 存在且结构合格", 8, 0, "未提供 llms.txt"))
    checks.append(_chk("B2", "llms-full.txt / Markdown 端点", 3, 3 if llms_full else 0,
                       "" if llms_full else "未提供"))
    checks.append(_chk("B3", "ai.txt / .well-known", 2, 2 if ai_txt else 0,
                       "" if ai_txt else "未提供"))
    sm = bool(robots and robots.get("sitemaps"))
    checks.append(_chk("B4", "sitemap 在 robots 中声明", 3, 3 if sm else 0,
                       "" if sm else "robots 未声明 Sitemap"))
    return {"key": "B", "name": "AI 发现文件", "weight": 16, "checks": checks}


def _dim_C(doc, jl):
    checks = []
    faq_nodes = []
    for p in jl["parsed"]:
        _find_nodes(p, "FAQPage", faq_nodes)
    faq_has_q = any(n.get("mainEntity") for n in faq_nodes)
    if faq_nodes and faq_has_q:
        c1 = 6
        n1 = ""
    elif faq_nodes:
        c1 = 2
        n1 = "声明 FAQPage 但无 Question,有造假风险"
    else:
        c1 = 0
        n1 = "无 FAQPage(实测带来 2.7x 引用率)"
    checks.append(_chk("C1", "FAQPage schema", 6, c1, n1))

    core = {"WebSite", "Organization", "Article", "BlogPosting"} & jl["types"]
    c2 = 4 if len(core) >= 2 else (2 if len(core) == 1 else 0)
    checks.append(_chk("C2", "核心 schema 覆盖(WebSite/Organization/Article)", 4, c2,
                       "已覆盖: " + ", ".join(sorted(core)) if core else "无核心 schema"))

    rich = _max_property_count(jl["parsed"])
    checks.append(_chk("C3", "Schema 丰富度(关键 schema ≥5 属性)", 3, 3 if rich >= 5 else (1.5 if rich >= 3 else 0),
                       "最大属性数 %d" % rich))

    if jl["block_count"] == 0:
        c4, n4 = 0, "页面无 JSON-LD"
    elif jl["has_error"]:
        c4, n4 = 0, "JSON-LD 解析报错"
    else:
        c4, n4 = 3, ""
    checks.append(_chk("C4", "Schema 有效性", 3, c4, n4))
    return {"key": "C", "name": "结构化数据 Schema", "weight": 16, "checks": checks,
            "_faq_claim_no_q": bool(faq_nodes) and not faq_has_q}


def _dim_D(doc):
    checks = []
    wc = doc.word_count()
    sents = doc.sentences()
    nums = doc.number_count()

    claim_sents = 0
    for s in sents:
        if re.search(r"\d", s) or _COPULA.search(s):
            claim_sents += 1
    density = (claim_sents / wc * 100) if wc else 0
    d1 = 6 if density >= 4 else (3 if density >= 2 else 0)
    checks.append(_chk("D1", "主张密度(≥4 可抽取事实/100词)", 6, d1,
                       "密度 %.1f/100词" % density))

    head = doc.text.replace("\n", " ")[:140]
    if re.search(r"(一句话|答案|TL;DR|TLDR|结论先行)", head) or re.search(r"\d", head) or _COPULA.search(head):
        d2 = 5
    elif re.search(r"\d", doc.text.replace("\n", " ")[:400]):
        d2 = 3
    else:
        d2 = 0
    checks.append(_chk("D2", "答案前置(前 100 词内给直接答案)", 5, d2))

    avg = doc.avg_sentence_words()
    if 12 <= avg <= 30:
        d3 = 3
    elif 8 <= avg < 12 or 30 < avg <= 45:
        d3 = 1.5
    else:
        d3 = 0
    checks.append(_chk("D3", "句长(平均 15~20 词)", 3, d3, "平均 %.1f 词/句" % avg))

    if 800 <= wc <= 1500:
        d4, n4 = 4, ""
    elif 500 <= wc < 800 or 1500 < wc <= 2500:
        d4, n4 = 2, ""
    elif wc > 3000:
        d4, n4 = 0, "过长(>3000词)抽取率骤降"
    else:
        d4, n4 = 0, "过短(<500词)"
    checks.append(_chk("D4", "信息密度/篇幅(800~1500词最优)", 4, d4,
                       n4 or ("%d 词" % wc)))

    ext = len(doc.external_links())
    if nums >= 3 and ext >= 1:
        d5 = 4
    elif nums >= 3 or ext >= 1:
        d5 = 2
    else:
        d5 = 0
    checks.append(_chk("D5", "统计数据+外部引用", 4, d5,
                       "数字 %d 个,外链 %d 个" % (nums, ext)))
    return {"key": "D", "name": "内容可抽取性", "weight": 22, "checks": checks}


def _dim_E(doc):
    checks = []
    h1 = [h for h in doc.headings if h[0] == 1]
    levels = [lvl for lvl, _ in doc.headings]
    jump = False
    prev = 0
    for lvl in levels:
        if prev and lvl > prev + 1:
            jump = True
        prev = lvl
    if len(h1) == 1 and not jump:
        e1, n1 = 4, ""
    elif len(h1) == 1:
        e1, n1 = 2, "标题层级跳级"
    else:
        e1, n1 = 0, "H1 数量为 %d(应为 1)" % len(h1)
    checks.append(_chk("E1", "标题层级(单一 H1 不跳级)", 4, e1, n1))

    lists_tables = doc.counts["ul"] + doc.counts["ol"] + doc.counts["table"]
    checks.append(_chk("E2", "列表与表格", 3, 3 if lists_tables >= 1 else 0,
                       "list/table 共 %d 个" % lists_tables))

    qa = any(_QA_PATTERNS.search(t) for _, t in doc.headings)
    defblk = doc.counts["dl"] + doc.counts["details"]
    checks.append(_chk("E3", "定义块/Q&A 标题", 3, 3 if (qa or defblk) else 0))

    sents = doc.sentences()
    triple = sum(1 for s in sents if _COPULA.search(s))
    ratio = (triple / len(sents)) if sents else 0
    e4 = 3 if ratio >= 0.3 else (1.5 if ratio >= 0.15 else 0)
    checks.append(_chk("E4", "语义三元组密度(主谓宾)", 3, e4, "%.0f%% 句子" % (ratio * 100)))

    thin = doc.visible_text_len < 200
    checks.append(_chk("E5", "无反引用信号(非薄内容/堆砌)", 3, 0 if thin else 3,
                       "可见正文过薄" if thin else ""))
    return {"key": "E", "name": "内容结构与可解析性", "weight": 16, "checks": checks}


def _dim_F(doc, jl):
    checks = []
    person = []
    for p in jl["parsed"]:
        _find_nodes(p, "Person", person)
    author_sig = doc.has_rel_author or bool(person) or bool(re.search(r"(作者|撰文|by\s+\w)", doc.text, re.IGNORECASE))
    checks.append(_chk("F1", "作者署名 + Person schema", 3, 3 if author_sig else 0))

    kg = _has_sameas(jl["parsed"]) or any(
        any(h in lk.get("href", "") for h in _KG_HOSTS) for lk in doc.links)
    checks.append(_chk("F2", "知识图谱外链(sameAs/Wikipedia/LinkedIn)", 3, 3 if kg else 0))

    org_nodes = []
    for p in jl["parsed"]:
        _find_nodes(p, "Organization", org_nodes)
    org_name = None
    for n in org_nodes:
        if isinstance(n.get("name"), str):
            org_name = n["name"]
            break
    if org_name and org_name in doc.text:
        f3 = 3
    elif org_name:
        f3 = 1.5
    else:
        f3 = 0
    checks.append(_chk("F3", "实体一致性(品牌名跨页一致)", 3, f3))

    iso_date = any(re.search(r"\d{4}-\d{2}-\d{2}", t.get("datetime") or "") for t in doc.time_attrs)
    iso_in_jsonld = any(re.search(r'"date(Modified|Published)"\s*:\s*"\d{4}-\d{2}-\d{2}', b)
                        for b in doc.jsonld_blocks)
    recent_year = bool(re.search(r"\b(2024|2025|2026|2027)\b", doc.text))
    if iso_date or iso_in_jsonld:
        f4 = 3
    elif recent_year:
        f4 = 1.5
    else:
        f4 = 0
    checks.append(_chk("F4", "内容新鲜度(dateModified/近期年份)", 3, f4))
    return {"key": "F", "name": "信任、实体与权威", "weight": 12, "checks": checks}


# --------------------------------------------------------------------------
# top-level
# --------------------------------------------------------------------------
def score_document(doc, robots_text=None, llms_text=None, llms_full=False,
                   ai_txt=False, market="auto"):
    if market == "auto":
        market = "cn" if doc.is_cjk else "global"

    jl = analyze_jsonld(doc.jsonld_blocks)
    robots = parse_robots(robots_text) if robots_text is not None else None

    dims = []
    if robots is not None:
        dims.append(_dim_A(robots, market))
    if robots is not None or llms_text is not None or llms_full or ai_txt:
        dims.append(_dim_B(robots, llms_text, llms_full, ai_txt))
    dims.append(_dim_C(doc, jl))
    dims.append(_dim_D(doc))
    dims.append(_dim_E(doc))
    dims.append(_dim_F(doc, jl))

    included_weight = 0
    earned = 0.0
    for d in dims:
        dw = sum(c["weight"] for c in d["checks"])
        de = sum(c["earned"] for c in d["checks"])
        d["weight_evaluated"] = dw
        d["earned"] = round(de, 2)
        included_weight += dw
        earned += de

    # vetoes
    vetoes = []
    if doc.visible_text_len < 150 and doc.counts["script"] > 0:
        vetoes.append("正文疑似 CSR 空壳(可见文本过少 + 有脚本),AI 爬虫拿不到内容")
    c_dim = next((d for d in dims if d["key"] == "C"), None)
    if c_dim and c_dim.get("_faq_claim_no_q"):
        vetoes.append("声明 FAQPage 但无问答对,涉嫌 schema 造假")
    if robots is not None:
        a_dim = next((d for d in dims if d["key"] == "A"), None)
        if a_dim and all(c["earned"] == 0 for c in a_dim["checks"][:3]):
            vetoes.append("全部 AI 检索爬虫被屏蔽,技术上不可被引用")

    raw_100 = (earned / included_weight * 100) if included_weight else 0
    score_100 = math.floor(raw_100)
    if vetoes:
        score_100 = min(score_100, 60)

    if score_100 >= 85:
        grade = "优"
    elif score_100 >= 70:
        grade = "良"
    elif score_100 >= 40:
        grade = "待优化"
    else:
        grade = "危急"

    # GEO score (A+B+C+D) and SEO score (C+E+F) over their evaluated weights
    def subset_score(keys):
        w = e = 0.0
        for d in dims:
            if d["key"] in keys:
                w += d["weight_evaluated"]
                e += d["earned"]
        return math.floor(e / w * 100) if w else None

    return {
        "market": market,
        "score": score_100,
        "grade": grade,
        "earned": round(earned, 2),
        "included_weight": included_weight,
        "geo_score": subset_score({"A", "B", "C", "D"}),
        "seo_score": subset_score({"C", "E", "F"}),
        "dimensions": dims,
        "vetoes": vetoes,
        "weakest": _weakest(dims),
    }


def _weakest(dims):
    rows = []
    for d in dims:
        for c in d["checks"]:
            if c["weight"] > 0:
                rows.append((c["earned"] / c["weight"], d["key"], c))
    rows.sort(key=lambda r: r[0])
    return [{"dim": k, "id": c["id"], "name": c["name"],
             "earned": c["earned"], "weight": c["weight"], "note": c["note"]}
            for _, k, c in rows[:5]]
