"""信源策略层(八层机制 2-4:索引 / 查询 / 检索)。

来源:WaytoAGI《GEO 内容工程》公开课(姚金刚)。会议把 GEO 拆成两半:
内容质量(八层 5-7,重排/装配/引用,对应 cescore)和信源策略(八层 2-4,索引/查询/检索)。
信源策略的核心:研究不同词、不同 AI 平台的信源偏好特征,再做有 AI 偏好的信源投放,
而非一上来就批量发。本模块给品类/词根 + 目标引擎,产出:
  层 3 查询:词根→问句矩阵(信息/商业/交易意图,覆盖查询改写后的关键词词组)
  层 2 索引:收录前置动作(国内求收录占平台,海外配 robots+sitemap+llms.txt)
  层 4 检索:引擎信源偏好诊断 + 分层投放 SOP(复用 platform_recommend 已核实权重表)
  闭环:监测 = 概率(25 次取均值)→ sov 看占位 → lostprompt 看竞品夺走 → 回填迭代

复用 platform_recommend 的信源权重表,不另起炉灶。纯标准库,确定性。

诚实红线(写进输出):
- 国内是求收录加占平台,海外是配 robots.txt;两套打法不混用。
- 信源权重是校准参数,海外每月 40-60% 翻盘,数字方向性。
- 别押单平台,4+ 平台一致覆盖抗波动约 70 倍,优先 earned media。
- 先诊断目标平台的真实信源偏好再投放,别凭这张表盲发。
"""

from . import platform_recommend as recommendlib

# 词根 → 三类意图问句模板(对应八层第 3 层查询的意图识别)
_INTENT_TEMPLATES = {
    "信息": ["{r}是什么", "{r}怎么用", "{r}原理", "{r}有哪些"],
    "商业": ["{r}哪个好", "{r}推荐", "{r}对比", "最好的{r}", "{r}排行"],
    "交易": ["{r}多少钱", "{r}怎么买", "{r}哪里买", "{r}价格"],
}

_CN_ENGINES = set(recommendlib.CN_ENGINES)


def _index_layer_flags(want_cn, want_overseas):
    """层 2 索引:收录前置动作。收录是国产 AI 可见的前置(求收录占平台)。"""
    actions = []
    if want_cn:
        actions += [
            "国内求收录:site:你的域名 在百度/搜狗/神马自查收录量,未收录先做主动推送(geo_cli baidu-push)。",
            "占平台:国产 AI 多靠生态索引(博查/搜狗/百度),独立站权重低,优先把内容铺到高权重生态平台(见下方投放 SOP)。",
            "ICP 备案核实并上页脚,不展示备案被国产 AI 收录吃亏。",
        ]
    if want_overseas:
        actions += [
            "海外配 robots:放行 GPTBot/ClaudeBot/PerplexityBot/Google-Extended 等 AI 爬虫,声明 sitemap。",
            "海外信源少且贵(官网为主),把官网做成事实锚点(Schema + FAQ),再靠第三方 earned media 放大。",
            "llms.txt 当 B2A 基础设施给 agent 读,不当排名杠杆。",
        ]
    return actions


def _query_layer(roots):
    """层 3 查询:词根→问句矩阵。AI 会把长句改写成关键词词组,要按意图覆盖。"""
    matrix = []
    for r in roots:
        r = r.strip()
        if not r:
            continue
        row = {"root": r, "by_intent": {}}
        for intent, tmpls in _INTENT_TEMPLATES.items():
            row["by_intent"][intent] = [t.format(r=r) for t in tmpls]
        matrix.append(row)
    return matrix


def _delivery_sop(rec_rows, has_cn, has_overseas):
    """层 4 检索 → 分层投放 SOP。按"跨引擎共识 + 本次最高分档"切 P0/P1/P2。

    用相对分档而非绝对硬阈值:单引擎时权重上限只有 3,绝对阈值 5 会让 P0 恒空、
    把命脉平台误降到次轮。这里保证单引擎的最高权重命脉平台也能进 P0。
    """
    tiers = {"P0": [], "P1": [], "P2": []}
    max_s = max((r["score"] for r in rec_rows), default=0)
    for r in rec_rows:
        s = r["score"]
        n_eng = len(r["feeds_engines"])
        # P0:跨引擎共识(喂 2+ 目标引擎)或本次结果最高分档(命脉,单引擎也能进)
        if (n_eng >= 2 and s >= 3) or s >= 5 or (s == max_s and s >= 3):
            tier = "P0"
        elif s >= 2:
            tier = "P1"
        else:
            tier = "P2"
        tiers[tier].append({
            "platform": r["platform"], "score": s,
            "feeds_engines": r["feeds_engines"], "sources": r["sources"],
        })
    first_tier = "P0" if tiers["P0"] else ("P1" if tiers["P1"] else "P2")
    cadence = ("先发 %s 首档(跨引擎共识/命脉平台)试投 → 跑诊断闭环看是否被引 → "
               "用反馈决定下一档放量,别一上来批量发。" % first_tier)
    sop = {
        "tiers": tiers,
        "one_draft_four_forms": ["原文长稿(官网/公众号)", "问答体(知乎/百度知道/Quora)",
                                 "榜单/对比体(高引用结构)", "短视频带字幕(抖音/B站/YouTube)"],
        "cadence": cadence,
        "principles": [],
    }
    if has_cn:
        sop["principles"].append("国内:平台依附,生态账号矩阵比独立站权重高,发布成本低可多平台铺。")
    if has_overseas:
        sop["principles"].append("海外:域名主权 + earned media,信源少成本高,别押单平台(4+ 平台抗波动约 70 倍)。")
    return sop


def plan(category, roots, engines, content_type=None, market="auto"):
    """信源策略总规划。"""
    roots = roots or ([category] if category else [])
    resolved = recommendlib._resolve(engines) if engines else []
    # 识别不出的引擎(拼错/不存在):_resolve 会原样透传,这里挑出来提示,别静默出空规划
    unrecognized = [e for e in resolved
                    if e not in _CN_ENGINES and not recommendlib._is_overseas(e)]
    has_cn = any(e in _CN_ENGINES for e in resolved)
    has_overseas = any(recommendlib._is_overseas(e) for e in resolved)
    if market == "auto":
        market = "cn" if has_cn and not has_overseas else ("global" if has_overseas and not has_cn else "auto")

    rec = recommendlib.recommend(engines, content_type=content_type) if engines else {"recommendations": []}
    sop = _delivery_sop(rec["recommendations"], has_cn, has_overseas)

    # 给了引擎但一个都没识别 → 收录指引兜底给国内+海外双份,避免空规划误导
    idx_cn = has_cn or market == "cn" or (bool(resolved) and not has_cn and not has_overseas)
    idx_overseas = has_overseas or market == "global" or (bool(resolved) and not has_cn and not has_overseas)

    return {
        "category": category,
        "target_engines": resolved,
        "unrecognized_engines": unrecognized or None,
        "content_type": content_type or None,
        "market": market,
        "layer2_index": _index_layer_flags(idx_cn, idx_overseas),
        "layer3_query_matrix": _query_layer(roots),
        "layer4_source_preference": rec["recommendations"],
        "delivery_sop": sop,
        "diagnosis_loop": [
            "监测=概率:每个目标问句在每个平台用同样方式重复检索 5 次、覆盖约 5 个目标平台(共约 25 次),"
            "取均值=品牌被推荐概率;采样越多越稳,报采样置信度。",
            "用 geo_cli prompts 把上面的词根问句矩阵扩成完整 buyer prompt 集,逐条去目标平台问。",
            "把 AI 回答喂 geo_cli sov 看自己占位、喂 lostprompt 看哪些问句被竞品夺走。",
            "按反馈回填信源:被竞品占的问句,补它占位的那类平台/信源,再投放、再监测,迭代提升概率。",
        ],
        "note": "信源策略打八层机制的 2-4 层(索引/查询/检索),与 cescore 的内容质量层(5-7)互补。"
                "国内求收录加占平台,海外配 robots,两套不混用。信源权重是校准参数,海外方向性、每月翻盘。"
                "先诊断目标平台真实信源偏好再投放,别凭表盲发,别押单平台。",
    }


def render_markdown(p):
    out = ["# 信源策略规划(八层机制 2-4:索引/查询/检索)", ""]
    head = "品类: %s" % (p["category"] or "(未填)")
    if p["target_engines"]:
        head += " | 目标引擎: " + "、".join(p["target_engines"])
    if p["content_type"]:
        head += " | 内容类型: " + p["content_type"]
    head += " | 市场: " + p["market"]
    out.append(head)
    if p.get("unrecognized_engines"):
        out.append("")
        out.append("⚠️ 未识别的引擎(已透传,信源偏好诊断对它无数据): %s。"
                   "请核对引擎名(豆包/元宝/deepseek/kimi/文心/通义/chatgpt/perplexity/gemini/claude 等),"
                   "或用 cn-all / overseas-all。" % "、".join(p["unrecognized_engines"]))
    out.append("")
    out.append("> " + p["note"])
    out.append("")

    out.append("## 层 3 查询:词根→问句矩阵")
    if p["layer3_query_matrix"]:
        for row in p["layer3_query_matrix"]:
            out.append("**%s**" % row["root"])
            for intent, qs in row["by_intent"].items():
                out.append("- %s意图:%s" % (intent, " / ".join(qs)))
    else:
        out.append("(未给词根,用 --root 传入)")
    out.append("")

    out.append("## 层 2 索引:收录前置动作")
    for a in p["layer2_index"]:
        out.append("- " + a)
    out.append("")

    out.append("## 层 4 检索:信源偏好诊断 + 分层投放 SOP")
    sop = p["delivery_sop"]
    tier_label = {"P0": "跨引擎共识/命脉首发", "P1": "单引擎高权重/次轮",
                  "P2": "补充覆盖,按品类回判"}
    for tier in ["P0", "P1", "P2"]:
        items = sop["tiers"][tier]
        if not items:
            continue
        out.append("**%s(%s)**" % (tier, tier_label[tier]))
        for it in items:
            out.append("- %s(加权 %d,喂 %s)" % (
                it["platform"], it["score"], "、".join(it["feeds_engines"])))
    if sop["tiers"]["P2"]:
        out.append("(P2 不等于不重要:B2B 看 G2、本地看 Yelp 这类品类决定项可能落这档,按你的品类回判,别照字面砍。)")
    out.append("")
    out.append("一稿四态:" + " / ".join(sop["one_draft_four_forms"]))
    out.append("发布节奏:" + sop["cadence"])
    for pr in sop["principles"]:
        out.append("- " + pr)
    out.append("")

    out.append("## 闭环:监测=概率,按反馈迭代信源")
    for d in p["diagnosis_loop"]:
        out.append("- " + d)
    return "\n".join(out)
