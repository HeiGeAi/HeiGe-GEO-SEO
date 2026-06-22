"""GEO 归因工具包(v1.3 中外双轨)。

AI 来源流量转化率高(实测最高 15.9% vs 自然流量 1.76%),但 35%-70% 掉进
GA4 的 Direct 黑洞。本模块生成归因物料:GA4 渠道组正则(含国内引擎)+ UTM 规范
+ 服务器日志 AI 爬虫 UA 解析(区分中国 vs 海外引擎,分训练/检索/用户触发三类)。
纯规则+正则,100% 离线。

关键认知:
- 爬虫 UA 在 access log 里,真人点击 referrer 在 GA4 里,两件事彻底分开。
- 5.7% 的 AI UA 是伪造的,高置信需比对官方 IP JSON,本工具只做 UA 层初筛。
- Grok / Bytespider / Copilot-agent 是 UA 盲区(伪造浏览器/住宅IP),日志层测不到,只能靠 referrer 兜底。
"""

import re


# AI 引擎 referrer 域名(真人点引用进站,出现在 GA4/Referer)
_AI_REFERRER = {
    # 海外
    "chatgpt": ["chatgpt.com", "chat.openai.com", "openai.com"],
    "perplexity": ["perplexity.ai"],
    "claude": ["claude.ai", "anthropic.com"],
    "gemini": ["gemini.google.com", "bard.google.com"],
    "copilot": ["copilot.microsoft.com", "bing.com/chat", "edgeservices.bing.com"],
    "grok": ["grok.com", "grok.x.com", "x.ai"],
    "metaai": ["meta.ai"],
    "mistral": ["mistral.ai"],
    "you": ["you.com"],
    "ai-index": ["aisearchindex.space"],
    # 国内
    "doubao": ["doubao.com"],
    "wenxin": ["yiyan.baidu.com"],
    "tongyi": ["tongyi.aliyun.com"],
    "yuanbao": ["yuanbao.tencent.com"],
    "kimi": ["kimi.moonshot.cn", "kimi.com"],
    "deepseek-cn": ["deepseek.com"],
}

# AI 爬虫 UA -> (用途 train/search/user, region cn/overseas, 引擎)
_AI_BOT_UA = {
    # 海外 · 训练
    "GPTBot": ("train", "overseas", "OpenAI"),
    "ClaudeBot": ("train", "overseas", "Anthropic"),
    "Google-Extended": ("train", "overseas", "Google"),
    "Applebot-Extended": ("train", "overseas", "Apple"),
    "Amazonbot": ("train", "overseas", "Amazon"),
    "Meta-ExternalAgent": ("train", "overseas", "Meta"),
    "CCBot": ("train", "overseas", "CommonCrawl"),
    # 海外 · 检索索引
    "OAI-SearchBot": ("search", "overseas", "OpenAI"),
    "Claude-SearchBot": ("search", "overseas", "Anthropic"),
    "PerplexityBot": ("search", "overseas", "Perplexity"),
    "Googlebot": ("search", "overseas", "Google"),
    "bingbot": ("search", "overseas", "Microsoft/Copilot/Meta/DDG"),
    "DuckAssistBot": ("search", "overseas", "DuckDuckGo"),
    "YouBot": ("search", "overseas", "You.com"),
    "Bravebot": ("search", "overseas", "Brave/Mistral"),
    "Applebot": ("search", "overseas", "Apple"),
    # 海外 · 用户触发(代表"有人正在 AI 里读你")
    "ChatGPT-User": ("user", "overseas", "OpenAI"),
    "Claude-User": ("user", "overseas", "Anthropic"),
    "Perplexity-User": ("user", "overseas", "Perplexity"),
    "MistralAI-User": ("user", "overseas", "Mistral"),
    "Meta-ExternalFetcher": ("user", "overseas", "Meta"),
    "Google-NotebookLM": ("user", "overseas", "Google"),
    # 国内
    "Baiduspider": ("search", "cn", "百度/文心"),
    "Sogou web spider": ("search", "cn", "搜狗/元宝"),
    "Bytespider": ("train", "cn", "字节/豆包"),
    "PetalBot": ("train", "cn", "华为/盘古"),
    "YisouSpider": ("search", "cn", "神马/夸克"),
    "DeepSeekBot": ("train", "cn", "DeepSeek"),
}

# UA 盲区:测不到,只能靠 referrer 兜底
_UA_BLINDSPOTS = [
    "Grok/xAI(无爬虫文档,住宅IP轮换+伪造Safari/Chrome UA,日志层不可见,靠 referrer grok.com/x.ai 估算)",
    "Copilot Actions / 自主 agent(用标准 Edge/Chromium UA,无 bot 信号)",
    "Bytespider(伪造 UA + 违反 robots,当 scraper)",
]


def gen_ga4_regex():
    """GA4 自定义渠道组正则(99% 可测 AI 流量,含国内),放 Referral 规则上方。"""
    domains = []
    for v in _AI_REFERRER.values():
        for d in v:
            domains.append(d.replace(".", r"\."))
    return "|".join(domains)


def gen_utm(base_url, engine="ai", campaign="geo"):
    sep = "&" if "?" in base_url else "?"
    return "%s%sutm_source=llm&utm_medium=ai_answer&utm_campaign=%s&utm_content=%s" % (
        base_url, sep, campaign, engine)


def parse_access_log(log_text):
    """解析 access log,按 region(中国/海外)+ 用途(训练/检索/用户触发)分桶统计
    各 AI 爬虫的命中次数和抓取页面。回答'哪个 AI 抓过你、抓了哪些页'。"""
    hits = {}
    pages = {}
    line_re = re.compile(r'"(?:GET|POST|HEAD)\s+(\S+).*?"\s+\d+\s+\S+\s+"[^"]*"\s+"([^"]*)"')
    for line in log_text.splitlines():
        m = line_re.search(line)
        path, ua = (m.group(1), m.group(2)) if m else (None, line)
        for bot in _AI_BOT_UA:
            if bot in ua:
                hits[bot] = hits.get(bot, 0) + 1
                if path:
                    pages.setdefault(bot, {})
                    pages[bot][path] = pages[bot].get(path, 0) + 1
                break

    by_bot = []
    region_totals = {"cn": 0, "overseas": 0}
    purpose_totals = {"train": 0, "search": 0, "user": 0}
    for bot, n in sorted(hits.items(), key=lambda kv: -kv[1]):
        purpose, region, engine = _AI_BOT_UA[bot]
        region_totals[region] += n
        purpose_totals[purpose] += n
        top_pages = sorted(pages.get(bot, {}).items(), key=lambda kv: -kv[1])[:5]
        by_bot.append({"bot": bot, "engine": engine, "purpose": purpose,
                       "region": region, "hits": n,
                       "top_pages": [{"path": p, "hits": c} for p, c in top_pages]})
    return {
        "bots_seen": len(hits),
        "total_ai_hits": sum(hits.values()),
        "by_region": region_totals,
        "by_purpose": purpose_totals,
        "by_bot": by_bot,
        "realtime_read_hits": purpose_totals["user"],
        "blindspots": _UA_BLINDSPOTS,
        "note": "用户触发类(*-User)才代表有人正在 AI 里读你;训练/索引类不是实时检索。"
                "Grok/Copilot-agent 测不到,需看 referrer。",
    }


def render_kit(site_url=None):
    out = ["# GEO 归因物料包(中外双轨)", ""]
    out.append("## 1. GA4 自定义渠道组正则(把 AI 流量从 Direct 黑洞捞出来)")
    out.append("```\n" + gen_ga4_regex() + "\n```")
    out.append("放在 GA4 > 管理 > 渠道组,新建 'AI Referral',regex 放 Referral 规则**上方**(自上而下匹配)。")
    out.append("注意:GA4 原生 AI Assistant 频道(2026-05)只认 ChatGPT/Gemini/Claude 三家、不回填、35%-70% 无 referrer 落 Direct,所以仍需自建。")
    out.append("")
    out.append("## 2. UTM 命名规范(给 llms.txt/answers.json 出站链接打标)")
    if site_url:
        out.append("```\n" + gen_utm(site_url, "chatgpt") + "\n```")
    out.append("ChatGPT 现已自动加 utm_source=chatgpt.com,归因变准。")
    out.append("")
    out.append("## 3. 服务器日志 AI 爬虫识别(中外分桶 + 三分类)")
    out.append("用 `geo_cli attribution --log access.log` 解析,区分国内(Baiduspider/Sogou/Bytespider 等)")
    out.append("与海外(GPTBot/OAI-SearchBot/PerplexityBot/ClaudeBot/bingbot 等),并分训练/检索/用户触发三类。")
    out.append("")
    out.append("## 4. UA 盲区(测不到,靠 referrer 兜底)")
    for b in _UA_BLINDSPOTS:
        out.append("- " + b)
    out.append("")
    out.append("## 5. 反伪造")
    out.append("5.7% 的 AI UA 是假的。高置信需比对官方 IP JSON(gptbot.json/searchbot.json/perplexitybot.json)或反查 DNS。")
    return "\n".join(out) + "\n"
