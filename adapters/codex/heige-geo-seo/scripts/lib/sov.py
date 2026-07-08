"""Share of Voice 度量 + prompt 覆盖率 + 采样置信度。

度量学 100% 离线。输入是宿主 agent / 人工跑大模型后回填的"prompt→answer"记录,
脚本算可见度,不自己联网。对齐国内口径:提及率 + SOV 声量占比 + 推荐排名 + 别名合并。

records: list of {prompt, engine, answer[, run, turn, conversation]}
"""

import re


# 竞争位基准阈值(Mention SoV / Weighted SoV),来自竞品方法学
_TIERS = [
    ("领导者", 40, 35),
    ("Top3 挑战者", 20, 15),
    ("Top10", 10, 7),
    ("新进入者", 0, 0),
]

# host 只吃合法域名字符,端口单独吞掉不进域名;URL 后紧跟的中文/全角标点不再被吞进 host
_URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+)(?::\d+)?")
# 缺失语境识别:AI 说"找不到你/未收录你"时品牌串虽出现但不算被推荐。
# 关键是贴身相邻:缺失标记必须紧挨品牌(前或后),不是同句任意位置命中就抑制,
# 否则会误杀"黑哥AI找不到对手""没找到比黑哥AI更好的"这类真提及(v1.10 首版的坑)。
# 标记与品牌之间允许空白(中英混排里英文品牌两侧惯例带空格,如"找不到 HeiGeAI")。
# 品牌"前"紧跟缺失动词(可隔"叫做/名为/一个"等实体引导词):没找到 [明确叫做] BRAND
_ABS_BEFORE = re.compile(
    r"(?:没有?找到|没找到|未找到|找不到|搜不到|查不到|没有查到|查无此?|"
    r"搜索结果(?:中|里)?没有|结果(?:中|里)?没有|没听说过|记错(?:了)?名(?:字|称)?|"
    r"并?不存在|(?:目前|现在|市面上|市场上|国内|全网)?并?(?<!有)没有)"
    r"\s*(?:明确|正式|确切)?\s*(?:叫做|名为|名叫|称为|叫|一个|这个|这款|该\S{0,4})?\s*$")
# 品牌"后"紧跟缺失标记(可隔"这个平台/该工具"):BRAND [这个平台] 尚未收录 / 不存在
# "不存在"要求贴到小句末尾,否则"黑哥AI不存在套路"这类真提及会被误杀
_ABS_AFTER = re.compile(
    r"^\s*(?:这个|这款|该)?\s*(?:平台|工具|品牌|产品|网站|应用|软件)?\s*"
    r"(?:(?:未|尚未|暂未|暂无|还没|一直没|均未)(?:被)?.{0,5}?收录|不在收录|查无此|并?不存在\s*$)")
# 缺失动词命中但品牌后是比较级/属性结构时,整句其实是"找不到比它更好/找不到它的缺点"类
# 最高级夸奖,不抑制(与上面注释声明的设计意图一致)
_KEEP_AFTER = re.compile(
    r"^\s*(?:更|最|比|一样|这样|这么|般|的\s*(?:缺点|短板|不足|毛病|对手|敌手|替代|竞品))")

# 被引语境情感词典(确定性):正面 = 被推荐,负面 = 被劝退
# "不X" 类否定由否定前缀检测处理,_NEG_WORDS 只放本身就负的词
_POS_WORDS = ("推荐", "首选", "最佳", "最好", "领先", "优秀", "值得", "好用",
              "可靠", "best", "top", "recommend", "leading",
              "excellent", "great", "reliable", "preferred")
_NEG_WORDS = ("避免", "别用", "争议", "问题", "缺点", "弱", "风险", "投诉",
              "崩", "慎用", "avoid", "issue", "problem", "downside",
              "poor", "weak", "risk", "controversy")
_NEG_PREFIX = ("不", "没", "无", "别", "勿", "未", "莫", "非", "算不上", "称不上")
# 英文否定词:窗口按词取(前 2 个词),半角 3 字符窗口逮不住 "not recommend"
_EN_NEG = ("not", "no", "never", "hardly", "barely", "cannot", "neither", "nor",
           "don't", "doesn't", "didn't", "won't", "wouldn't", "isn't", "aren't",
           "wasn't", "can't", "couldn't", "shouldn't")
# "没问题/无风险"是夸奖不是负面:先按正面计数并从文本剔除,防止裸词"问题/风险"记负面。
# 长习语在前,避免短的先剔除截断长的
_NEG_IDIOM_POS = ("没有任何问题", "没有什么问题", "没什么问题", "没有问题", "没啥问题",
                  "没问题", "不成问题", "没毛病", "没有任何风险", "没什么风险",
                  "没有风险", "无风险", "零风险", "没有缺点", "没什么缺点", "无缺点")
# 英文情感词加 ASCII 边界,防 desktop 命中 top、topic 命中 top 这类裸子串误报;
# 允许 s/es/ed/ing 常见词形变化,数字后缀(top10)不挡
_ASCII_HIT = {w: re.compile(r"(?<![a-z0-9])" + re.escape(w) + r"(?:s|es|ed|ing)?(?![a-z0-9])")
              for w in (_POS_WORDS + _NEG_WORDS) if w.isascii()}


def _hit_positions(text, word):
    """word 在 text(已小写)里的命中位置。ASCII 词走边界正则,CJK 词走子串。"""
    w = word.lower()
    if w in _ASCII_HIT:
        return [m.start() for m in _ASCII_HIT[w].finditer(text)]
    out = []
    start = 0
    while True:
        i = text.find(w, start)
        if i < 0:
            return out
        out.append(i)
        start = i + len(w)


def _negated_before(text, i):
    """位置 i 处的情感词是否被否定修饰:中文查前 3 字符,英文查前 2 个词。"""
    pre = text[max(0, i - 24):i]
    if any(n in pre[-3:] for n in _NEG_PREFIX):
        return True
    words = re.findall(r"[a-z']+", pre)
    return any(w in _EN_NEG for w in words[-2:])


def _count_sentiment(win):
    """窗口内数正负面信号,正面词被否定前缀修饰则翻转为负面。"""
    text = win.lower()
    pos = neg = 0
    for idiom in _NEG_IDIOM_POS:
        c = text.count(idiom)
        if c:
            pos += c
            text = text.replace(idiom, " ")
    for w in _NEG_WORDS:
        neg += len(_hit_positions(text, w))
    for w in _POS_WORDS:
        for i in _hit_positions(text, w):
            if _negated_before(text, i):
                neg += 1
            else:
                pos += 1
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
    # 端口与句尾半角点兜底剥掉,保证归属比对只看主机名
    host = host.lower().split(":")[0].rstrip(".")
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


def _first_present_idx(answer, alias):
    """品牌串首个"真实出现"的下标。出现在"没找到/未收录/不存在"窗口里的不算(AI 说找不到你
    不等于推荐你),全部落在缺失语境则返回 None。真实采集发现:秘塔答"没有找到黑哥AI"被误判成提及。"""
    start = 0
    n = len(alias)
    stops = "。！？；，、：!?;,\n"
    while True:
        p = answer.find(alias, start)
        if p < 0:
            return None
        # 前片:当前小句句首→品牌前;后片:品牌后→当前小句句尾。缺失标记必须贴身相邻才抑制
        lo = p
        while lo > 0 and answer[lo - 1] not in stops:
            lo -= 1
        hi = p + n
        while hi < len(answer) and answer[hi] not in stops:
            hi += 1
        after = answer[p + n:hi]
        if _ABS_BEFORE.search(answer[lo:p]) and not _KEEP_AFTER.match(after):
            start = p + n
            continue
        if _ABS_AFTER.match(after):
            start = p + n
            continue
        return p


def parse_answer(answer, brands, aliases=None):
    """返回 {brand: position}(按首次出现顺序排名,1=最先)+ 引用域名列表。"""
    first_idx = {}
    for b in brands:
        idx = None
        for alias in _aliases_for(b, aliases):
            if not alias:
                continue
            p = _first_present_idx(answer, alias)
            if p is not None and (idx is None or p < idx):
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

    # SOV 档位阈值来自竞品对比方法学:单品牌模式下 mention_sov 恒 100%,
    # 评档必然是"领导者"假结论,无竞品时不评档
    tier = (classify_tier(mention_sov[brand], weighted_sov[brand])
            if competitors else "无竞品数据,不评档")

    engine_breakdown = {}
    for eng, pe in per_engine.items():
        engine_breakdown[eng] = sov(pe["mention"])

    # 多轮对话(仅当记录带 turn 字段):
    #   by_turn = 分轮命中率(每轮独立);turn_retention = 真留存(同一对话首轮命中后续是否仍在)
    has_turn = any("turn" in r for r in records)
    by_turn = None
    turn_retention = None
    if has_turn:
        # 对话配对:多轮对话里每轮问句天然不同,拿 prompt 配对必得 0% 留存。
        # 带 conversation 字段按 (engine, conversation) 分组;没有就按记录顺序
        # 每引擎重建:turn 不再递增(回到 <= 上一轮)即视为新对话开始
        tg = {}
        convs = []       # 每个元素 {turn: present},代表一段对话
        explicit = {}    # (engine, conversation) -> conv dict
        seq_last = {}    # engine -> (conv dict, 上一条的 turn)
        for r in records:
            t = r.get("turn", 1)
            present = brand in parse_answer(r.get("answer", ""), brands, aliases)["positions"]
            slot = tg.setdefault(t, [0, 0])
            slot[1] += 1
            if present:
                slot[0] += 1
            eng = r.get("engine", "default")
            if "conversation" in r:
                cd = explicit.get((eng, r["conversation"]))
                if cd is None:
                    cd = {}
                    explicit[(eng, r["conversation"])] = cd
                    convs.append(cd)
            else:
                prev = seq_last.get(eng)
                if prev is None or t <= prev[1]:
                    cd = {}
                    convs.append(cd)
                else:
                    cd = prev[0]
                seq_last[eng] = (cd, t)
            # 同轮重复采样任一次命中即算命中,别让后一条覆盖前一条
            cd[t] = cd.get(t, False) or present
        by_turn = {str(t): {"hit": h, "total": n,
                            "rate": round(h / n * 100, 1) if n else 0.0}
                   for t, (h, n) in sorted(tg.items())}
        base = kept = 0
        for turns in convs:
            if len(turns) < 2:
                continue  # 单轮对话没有留存概念,不进分母
            first_t = min(turns)
            if turns[first_t]:
                base += 1
                if any(p for t2, p in turns.items() if t2 > first_t):
                    kept += 1
        turn_retention = {
            "first_turn_present": base, "retained_later": kept,
            "retention_rate": round(kept / base * 100, 1) if base else None,
            "note": "首轮命中的多轮对话里,后续轮仍提到你的比例。被追问后翻盘=低留存。"
                    "记录可带 conversation 字段标对话归属;缺省按 turn 序就近配对。",
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
