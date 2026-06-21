"""GEO 归因工具包。

AI 来源流量转化率高(实测最高 15.9% vs 自然流量 1.76%),但 35%-70% 掉进
GA4 的 Direct 黑洞。本模块生成归因物料:GA4 渠道组正则(含国内引擎)+ UTM 规范
+ 服务器日志 AI 爬虫 UA 解析。纯规则+正则,100% 离线。
"""

import re


# 海外 + 国内 AI 引擎域名(渠道组正则用),定期扩
_AI_REFERRER_DOMAINS = [
    r"chatgpt\.com", r"chat\.openai\.com", r"perplexity\.ai", r"claude\.ai",
    r"gemini\.google\.com", r"copilot\.microsoft\.com", r"bing\.com/chat",
    # 国内
    r"doubao\.com", r"yiyan\.baidu\.com", r"tongyi\.aliyun\.com", r"qianwen",
    r"yuanbao\.tencent\.com", r"kimi\.moonshot\.cn", r"kimi\.com", r"deepseek\.com",
]

# AI 爬虫 UA(日志识别),用途三层
_AI_BOT_UA = {
    "GPTBot": "train", "OAI-SearchBot": "search", "ChatGPT-User": "user",
    "ClaudeBot": "train", "Claude-SearchBot": "search", "Claude-User": "user",
    "PerplexityBot": "search", "Perplexity-User": "user",
    "Google-Extended": "train", "Googlebot": "search", "bingbot": "search",
    "Bytespider": "train", "Amazonbot": "train", "Applebot": "search",
    "CCBot": "train", "Baiduspider": "search",
}


def gen_ga4_regex():
    """GA4 自定义渠道组正则,一键复制进 GA4。"""
    return "(" + "|".join(_AI_REFERRER_DOMAINS) + ")"


def gen_utm(base_url, engine="ai", campaign="geo"):
    """给出站链接打 UTM,把 AI earned 流量和实验流量分开。"""
    sep = "&" if "?" in base_url else "?"
    return "%s%sutm_source=llm&utm_medium=ai_answer&utm_campaign=%s&utm_content=%s" % (
        base_url, sep, campaign, engine)


def parse_access_log(log_text):
    """解析服务器 access log,统计各 AI 爬虫的命中次数 + 抓取的页面。
    支持常见 combined log 格式(UA 在引号里)。"""
    hits = {}
    pages = {}
    line_re = re.compile(r'"(?:GET|POST|HEAD)\s+(\S+).*?"\s+\d+\s+\S+\s+"[^"]*"\s+"([^"]*)"')
    for line in log_text.splitlines():
        m = line_re.search(line)
        if not m:
            # fallback: just look for UA token anywhere
            path, ua = None, line
        else:
            path, ua = m.group(1), m.group(2)
        for bot in _AI_BOT_UA:
            if bot in ua:
                hits[bot] = hits.get(bot, 0) + 1
                if path:
                    pages.setdefault(bot, {})
                    pages[bot][path] = pages[bot].get(path, 0) + 1
                break
    summary = []
    for bot, n in sorted(hits.items(), key=lambda kv: -kv[1]):
        top_pages = sorted(pages.get(bot, {}).items(), key=lambda kv: -kv[1])[:5]
        summary.append({"bot": bot, "purpose": _AI_BOT_UA[bot], "hits": n,
                        "top_pages": [{"path": p, "hits": c} for p, c in top_pages]})
    return {"bots_seen": len(hits), "total_ai_hits": sum(hits.values()),
            "by_bot": summary}


def render_kit(site_url=None):
    """输出一份完整归因物料(markdown)。"""
    out = ["# GEO 归因物料包", ""]
    out.append("## 1. GA4 自定义渠道组正则(把 AI 流量从 Direct 黑洞捞出来)")
    out.append("```\n" + gen_ga4_regex() + "\n```")
    out.append("在 GA4 > 管理 > 渠道组 新建自定义渠道 'AI Referral',会话来源匹配上面正则。")
    out.append("")
    out.append("## 2. UTM 命名规范(给 llms.txt/answers.json 的出站链接打标)")
    if site_url:
        out.append("```\n" + gen_utm(site_url, "chatgpt") + "\n```")
    out.append("统一 utm_source=llm、utm_medium=ai_answer、utm_campaign=geo、utm_content=<引擎>。")
    out.append("")
    out.append("## 3. 服务器日志 AI 爬虫识别")
    out.append("用 `geo_cli attribution --log access.log` 解析 access log,统计 GPTBot/")
    out.append("OAI-SearchBot/PerplexityBot/ClaudeBot/Bytespider 等的抓取频次和页面。")
    out.append("")
    out.append("## 4. Layer2 推断(无 referrer 的部分)")
    out.append("被 AI 引用页的 direct 流量抬升 + 品牌搜索增量 + CRM 来源捕获,靠时间相关性推断。")
    out.append("35%-70% 的 AI 会话没有 referrer,只靠 Layer1 会严重低估,必须叠 Layer2。")
    return "\n".join(out) + "\n"
