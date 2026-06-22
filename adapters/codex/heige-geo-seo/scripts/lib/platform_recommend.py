"""平台推荐引擎:给目标 AI 引擎(和内容类型),推荐发布在哪几个平台权重最高。

把已核实的信源权重表(国内新榜 1683.6 万条实证 newrank.cn/report/detail/433
+ 海外引用研究 Profound/Semrush/5W 等)从静态知识变成会推荐的引擎。
回答两类需求:
  正向: 我想被豆包+元宝引用,该发哪 → recommend(["豆包","元宝"])
  反向: 我发知乎能喂哪些 AI → reverse("知乎")
纯标准库,确定性。

诚实红线(写进输出):
- 权重是校准参数不是永恒真理,每条标了来源。
- 海外引用每月 40-60% 翻盘、半年 70-90% 换新,所有海外数字是方向性。
- 引擎间源池低重叠(ChatGPT vs Perplexity 仅 11%),必须按引擎差异化,别一张表打天下。
- 别押单平台:4+ 平台一致覆盖比单一自有博文抗波动约 70 倍,82-94% 引用来自 earned media。
"""

# weight: 3=high / 2=med / 1=low
# 每条 (平台, 权重, 来源, 理由)
_ENGINE_PLATFORMS = {
    # ===== 国内引擎(新榜 1683.6 万条实证为主) =====
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
    # ===== 海外引擎(按检索后端分三组:Bing系/Google系/自建系;数字方向性,每月翻盘) =====
    # Bing 系
    "chatgpt": [
        ("Wikipedia", 3, "Profound方向性:ChatGPT top10占47.9%", "ChatGPT 命脉,实体页"),
        ("Reddit", 3, "方向性:11.3% top10(曾60%骤降10%)", "真实讨论"),
        ("LinkedIn", 3, "2025-26黑马升至#5", "B2B/专业内容"),
        ("Forbes", 2, "方向性:6.8% top10", "编辑类背书"),
        ("G2", 2, "B2B准入门", "B2B SaaS 评测"),
        ("官网+Schema", 2, "需第三方放大", "事实锚点,走 Bing 索引"),
    ],
    "copilot": [
        ("官网+Schema", 3, "Bing索引+结构化", "Bing 收录即可被引,FAQ/schema"),
        ("Stack Overflow", 2, "技术权重高", "开发/IT 内容"),
        ("LinkedIn", 2, "企业源", "B2B"),
        ("Microsoft Learn/官方文档", 2, "微软生态偏好", "技术文档"),
    ],
    "metaai": [
        ("官网+Schema", 2, "Bing地基", "Bing 收录"),
        ("Instagram/Facebook", 2, "社交互动加权", "B2C 高互动公开内容"),
        ("本地/消费内容", 2, "消费品类偏好", "B2C/本地,引流价值低"),
    ],
    # Google 系(注意:Gemini 几乎不引 Reddit,仅 0.1%)
    "gemini": [
        ("YouTube", 3, "方向性:AIO 18.8% top10,命脉", "带字幕转录,教程/演示"),
        ("LinkedIn", 3, "方向性:13% top10", "B2B/专业"),
        ("Quora", 2, "方向性:14.3% top10", "问答"),
        ("Yelp", 2, "Google本地偏好", "本地 B2C"),
        ("官网+Schema", 2, "进 Google 前10", "Article/FAQ schema"),
    ],
    # 自建系
    "perplexity": [
        ("Reddit", 3, "方向性:曾占46.7% top10,引用最重", "真实讨论,引用密度最高引擎"),
        ("LinkedIn", 3, "B2B强", "专业内容"),
        ("G2", 3, "B2B评测约75%", "B2B SaaS 准入门"),
        ("NIH/学术", 2, "学术偏好", "健康/科研"),
        ("Quora", 2, "问答", "消费决策"),
    ],
    "claude": [
        ("LinkedIn", 3, "长文偏好", "B2B 思想领导力"),
        ("官方文档/官网", 3, "偏一手技术源", "结构化文档"),
        ("权威媒体", 2, "偏 NYT/Economist 等传统媒体", "编辑类"),
        ("GitHub", 2, "代码偏好", "开发/技术"),
    ],
    "grok": [
        ("X/Twitter", 3, "唯一以X当信源的引擎(独家)", "实时高互动帖,⚠️引用幻觉率历史最高"),
        ("Reddit", 2, "单期高引用", "社区讨论"),
    ],
    "you": [
        ("官方文档/官网", 2, "企业级多域可溯源", "B2B research,已转纯API"),
        ("学术/权威源", 2, "法律/监管/税务偏好", "B2B 深度"),
    ],
    "brave": [
        ("官网+Schema", 3, "完全独立索引30B+页,要单独收录", "别只盯 Google/Bing"),
        ("Reddit", 2, "独立召回", "讨论"),
    ],
    "mistral": [
        ("官网+Schema", 3, "走 Brave API,优化 Brave 即覆盖 Mistral", "欧洲市场"),
        ("欧洲媒体/AFP-AP", 2, "新闻走 AFP+AP 合作社", "新闻类被锁,性价比低"),
    ],
    "duckduckgo": [
        ("Wikipedia", 3, "DuckAssist 重度 Wikipedia", "词条准确"),
        ("官网+Schema", 2, "Bing 蓝链地基", "复用 ChatGPT 打法"),
    ],
}

# 内容类型 → 追加候选平台(平台, 适配引擎集, 提示)
_CONTENT_TYPE = {
    "video": [("抖音", ["豆包"], "字幕必写"), ("B站", ["豆包", "deepseek"], "完整字幕"),
              ("视频号", ["元宝"], "微信生态"),
              ("YouTube", ["gemini", "perplexity"], "人工校对字幕+章节时间戳+答案前置")],
    "tech": [("CSDN", ["deepseek", "kimi"], "技术问答高权重"),
             ("掘金", ["deepseek"], "技术垂类"),
             ("Stack Overflow", ["copilot", "chatgpt", "claude"], "原子化可切块"),
             ("GitHub", ["claude", "chatgpt"], "代码/开源文档"),
             ("Hacker News", ["chatgpt"], "技术创业权威")],
    "种草": [("小红书", ["豆包"], "消费决策正面命中"), ("微博", ["deepseek"], "时效")],
    "消费": [("小红书", ["豆包"], "消费决策"), ("微博", ["deepseek"], "时效热点")],
    "b2b": [("G2", ["perplexity", "chatgpt"], "B2B评测准入门,起步5-10条达阈值"),
            ("Capterra", ["chatgpt"], "中小企业,已被G2收购"),
            ("TrustRadius", ["chatgpt"], "企业级评测"),
            ("LinkedIn", ["claude", "perplexity", "gemini"], "1500-2000字长文,个人+公司双押")],
    "b2c": [("Trustpilot", ["chatgpt"], "B2C低摩擦评测,对冲G2垄断"),
            ("Reddit", ["perplexity", "chatgpt"], "真实社区,90/10规则"),
            ("YouTube", ["gemini"], "演示+字幕"),
            ("Yelp", ["gemini"], "本地服务")],
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
    "gemini": "gemini", "aio": "gemini", "google": "gemini", "ai-overviews": "gemini",
    "claude": "claude", "anthropic": "claude",
    "copilot": "copilot", "bing": "copilot", "microsoft": "copilot",
    "grok": "grok", "xai": "grok", "x": "grok",
    "metaai": "metaai", "meta": "metaai", "meta-ai": "metaai", "llama": "metaai",
    "you": "you", "youcom": "you", "you.com": "you",
    "brave": "brave", "leo": "brave",
    "mistral": "mistral", "lechat": "mistral", "le-chat": "mistral", "vibe": "mistral",
    "duckduckgo": "duckduckgo", "ddg": "duckduckgo", "duckassist": "duckduckgo",
}

CN_ENGINES = ["豆包", "元宝", "deepseek", "kimi", "文心", "通义"]
OVERSEAS_ENGINES = ["chatgpt", "gemini", "claude", "perplexity", "copilot",
                    "grok", "metaai", "you", "brave", "mistral", "duckduckgo"]


def _is_overseas(eng):
    return eng in OVERSEAS_ENGINES


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
    agg = {}
    for eng in engines:
        for plat, w, src, why in _ENGINE_PLATFORMS.get(eng, []):
            rec = agg.setdefault(plat, {"score": 0, "feeds": [], "sources": set()})
            rec["score"] += w
            rec["feeds"].append({"engine": eng, "weight": w, "why": why})
            rec["sources"].add(src)
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

    has_overseas = any(_is_overseas(e) for e in engines)
    note = ("权重为校准参数。国内主体来自新榜 1683.6 万条实证,文心为百度生态通识。"
            "海外为引用研究方向性口径。")
    if has_overseas:
        note += ("⚠️海外引用每月 40-60% 翻盘,数字仅方向性;引擎间源池低重叠须按引擎差异化;"
                 "别押单平台,4+ 平台一致覆盖抗波动约 70 倍,优先 earned media(第三方)。")
    return {"target_engines": engines, "content_type": content_type or None,
            "recommendations": rows, "note": note}


def reverse(platform):
    """反向:这个平台能喂哪些 AI 引擎。"""
    feeds = []
    q = (platform or "").strip()
    for eng, plats in _ENGINE_PLATFORMS.items():
        for plat, w, src, why in plats:
            if q == plat or (len(q) >= 2 and q in plat):
                feeds.append({"engine": eng, "weight": w, "source": src, "why": why,
                              "region": "海外" if _is_overseas(eng) else "国内"})
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
