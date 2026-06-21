"""平台推荐引擎:给目标 AI 引擎(和内容类型),推荐发布在哪几个平台权重最高。

把已核实的信源权重表(新榜 1683.6 万条实证 newrank.cn/report/detail/433
+ 百度/阿里生态通识 + 海外引用研究)从静态知识变成会推荐的引擎。
回答两类需求:
  正向: 我想被豆包+元宝引用,该发哪 → recommend(["豆包","元宝"])
  反向: 我发知乎能喂哪些 AI → reverse("知乎")
纯标准库,确定性。权重是校准参数不是永恒真理,每条标了来源。
"""

# weight: 3=high / 2=med / 1=low
# 每条 (平台, 权重, 来源, 理由)
_ENGINE_PLATFORMS = {
    "豆包": [
        ("今日头条", 3, "新榜实证", "字节系自有池,TOP5 信源占 3 个"),
        ("抖音", 3, "新榜实证", "抖音百科+字节生态,需字幕文本"),
        ("知乎", 2, "豆包补充源约20%", "专业问答高权重"),
        ("搜狐", 2, "新榜万金油", "跨 AI 高引用"),
        ("网易", 2, "新榜万金油", "跨 AI 高引用"),
    ],
    "元宝": [
        ("微信公众号", 3, "新榜实证", "独家信源,占比约 10%,别家 AI 进不来"),
        ("视频号", 2, "腾讯生态", "微信生态结构化信息"),
        ("搜狗收录页", 2, "元宝走搜狗", "搜狗索引是元宝实时来源"),
        ("搜狐", 1, "新榜万金油", "跨 AI 通吃"),
    ],
    "deepseek": [
        ("搜狐", 3, "新榜实证", "门户偏好,重时效"),
        ("百度百科", 3, "新榜实证", "百科权重高"),
        ("网易", 3, "新榜实证", "门户"),
        ("知乎", 2, "UGC 偏好", "社区问答"),
        ("今日头条", 2, "新榜万金油", "跨 AI 通吃"),
    ],
    "kimi": [
        ("微信公众号", 3, "新榜实证", "高频引用"),
        ("搜狐", 3, "新榜实证", "门户"),
        ("知乎", 2, "UGC 约 70%,知乎比重突出", "专业问答"),
    ],
    "文心": [
        ("百家号", 3, "百度生态通识(非新榜)", "百度亲儿子,优先收录"),
        ("百度百科", 3, "百度生态", "百科权重高"),
        ("百度知道", 2, "百度生态", "问答"),
        ("知乎", 1, "通用", "高权重问答"),
    ],
    "通义": [
        ("夸克收录页", 3, "阿里夸克联动", "夸克索引是通义来源"),
        ("知乎", 2, "通用", "权威源"),
    ],
    # 海外
    "chatgpt": [
        ("Reddit", 3, "全网引用之王约40%", "ChatGPT 高频"),
        ("Wikipedia", 3, "训练语料底座", "ChatGPT 主导 26-48%"),
        ("官网+Schema", 2, "事实锚点", "走 Bing 索引,重域名声誉"),
    ],
    "perplexity": [
        ("Reddit", 3, "引用首位", "Perplexity 偏好"),
        ("LinkedIn", 2, "B2B", "专业信号"),
        ("G2", 2, "评测站", "Perplexity 偏好"),
        ("官网+Schema", 2, "事实锚点", "实时 RAG"),
    ],
    "gemini": [
        ("YouTube", 3, "Google 自有被引最多", "转录即文本"),
        ("Wikipedia", 3, "实体图", "权威"),
        ("Reddit", 2, "高频", ""),
        ("官网+Schema", 2, "事实锚点", "贴近 Google 排名"),
    ],
    "claude": [
        ("权威源/官方文档", 2, "偏权威多源验证", "Claude 偏好"),
        ("官网+Schema", 2, "事实锚点", "默认不挂链,重品牌心智"),
    ],
}

# 内容类型 → 追加候选平台(平台, 适配引擎集, 提示)
_CONTENT_TYPE = {
    "video": [("抖音", ["豆包"], "字幕必写"), ("B站", ["豆包", "deepseek"], "完整字幕"),
              ("视频号", ["元宝"], "微信生态"), ("YouTube", ["gemini", "chatgpt"], "字幕转录")],
    "tech": [("CSDN", ["deepseek", "kimi"], "技术问答高权重"),
             ("掘金", ["deepseek"], "技术垂类"), ("知乎", ["豆包", "kimi"], "技术问答")],
    "种草": [("小红书", ["豆包"], "消费决策正面命中"), ("微博", ["deepseek"], "时效")],
    "消费": [("小红书", ["豆包"], "消费决策"), ("微博", ["deepseek"], "时效热点")],
}

_ENGINE_ALIAS = {
    "doubao": "豆包", "豆包": "豆包",
    "yuanbao": "元宝", "腾讯元宝": "元宝", "元宝": "元宝",
    "deepseek": "deepseek", "ds": "deepseek",
    "kimi": "kimi",
    "ernie": "文心", "文心": "文心", "文心一言": "文心", "文小言": "文心", "百度": "文心",
    "qwen": "通义", "千问": "通义", "通义": "通义", "通义千问": "通义",
    "chatgpt": "chatgpt", "gpt": "chatgpt", "openai": "chatgpt",
    "perplexity": "perplexity", "pplx": "perplexity",
    "gemini": "gemini", "aio": "gemini", "google": "gemini",
    "claude": "claude",
}

CN_ENGINES = ["豆包", "元宝", "deepseek", "kimi", "文心", "通义"]
OVERSEAS_ENGINES = ["chatgpt", "perplexity", "gemini", "claude"]


def _resolve(engines):
    out = []
    for e in engines:
        key = e.strip().lower()
        if key == "cn-all":
            out += CN_ENGINES
        elif key == "overseas-all":
            out += OVERSEAS_ENGINES
        else:
            out.append(_ENGINE_ALIAS.get(e.strip(), _ENGINE_ALIAS.get(key, e.strip())))
    # dedup, keep order
    seen = set()
    res = []
    for e in out:
        if e not in seen:
            seen.add(e)
            res.append(e)
    return res


def recommend(target_engines, content_type=None, top=None):
    """给目标引擎,推荐发哪些平台(按加权得分排序)。"""
    engines = _resolve(target_engines)
    agg = {}  # platform -> {score, feeds:[(engine,why)], sources:set}
    for eng in engines:
        for plat, w, src, why in _ENGINE_PLATFORMS.get(eng, []):
            rec = agg.setdefault(plat, {"score": 0, "feeds": [], "sources": set()})
            rec["score"] += w
            rec["feeds"].append({"engine": eng, "weight": w, "why": why})
            rec["sources"].add(src)
    # content-type boost
    ct = (content_type or "").lower()
    for plat, eng_list, hint in _CONTENT_TYPE.get(ct, []):
        relevant = [e for e in eng_list if e in engines] or eng_list
        rec = agg.setdefault(plat, {"score": 0, "feeds": [], "sources": set()})
        rec["score"] += 2
        rec["sources"].add("内容类型适配:%s" % hint)
        for e in relevant:
            rec["feeds"].append({"engine": e, "weight": 2, "why": hint})

    rows = []
    for plat, rec in agg.items():
        rows.append({
            "platform": plat,
            "score": rec["score"],
            "feeds_engines": sorted({f["engine"] for f in rec["feeds"]}),
            "rationale": rec["feeds"],
            "sources": sorted(rec["sources"]),
        })
    rows.sort(key=lambda r: (r["score"], len(r["feeds_engines"])), reverse=True)
    if top:
        rows = rows[:top]
    return {"target_engines": engines, "content_type": content_type or None,
            "recommendations": rows,
            "note": "权重为校准参数,主体来自新榜 1683.6 万条实证(豆包/元宝/DeepSeek/Kimi),文心为百度生态通识,海外为引用研究口径。"}


def reverse(platform):
    """反向:这个平台能喂哪些 AI 引擎。"""
    feeds = []
    for eng, plats in _ENGINE_PLATFORMS.items():
        for plat, w, src, why in plats:
            if platform in plat or plat in platform:
                feeds.append({"engine": eng, "weight": w, "source": src, "why": why})
    feeds.sort(key=lambda f: f["weight"], reverse=True)
    return {"platform": platform, "feeds_engines": feeds,
            "engine_count": len({f["engine"] for f in feeds})}


def render_markdown(result):
    out = ["# 平台发布推荐", ""]
    out.append("目标引擎: %s%s" % ("、".join(result["target_engines"]),
               (" | 内容类型: " + result["content_type"]) if result["content_type"] else ""))
    out.append("")
    out.append("> " + result["note"])
    out.append("")
    out.append("| 排名 | 平台 | 加权分 | 喂哪些 AI | 来源 |")
    out.append("|---|---|---|---|---|")
    for i, r in enumerate(result["recommendations"], 1):
        out.append("| %d | %s | %d | %s | %s |" % (
            i, r["platform"], r["score"], "、".join(r["feeds_engines"]),
            "、".join(r["sources"])))
    return "\n".join(out)
