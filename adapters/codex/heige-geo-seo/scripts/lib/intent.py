"""搜索意图分类器(SEO 的起点,GEO 也吃)。

给一个查询/标题,判信息/商业/交易/导航四类意图,映射到该做的内容类型 + schema +
GEO/SEO 战术。接进 brief 当前置输入,让内容骨架按意图分叉。纯标准库,确定性。

意图错配,GEO 也救不了:用户在问"最好的X"(商业对比),你给一篇产品落地页,
既进不了 AI 的对比榜也接不住交易。
"""

import re


# 每类意图的关键词信号(中英)
_SIGNALS = {
    "informational": [
        "什么是", "怎么", "如何", "为什么", "教程", "指南", "原理", "区别", "是什么",
        "怎么样", "什么意思", "how to", "what is", "why", "guide", "tutorial",
        "meaning", "explain", "difference",
    ],
    "commercial": [
        "最好", "最佳", "推荐", "对比", "哪个好", "哪家", "评测", "排行", "排名",
        "替代", "值得", "vs", "best", "top", "review", "compare", "comparison",
        "alternative", "which", "vs.",
    ],
    "transactional": [
        "购买", "价格", "多少钱", "下单", "优惠", "折扣", "试用", "注册", "下载",
        "报价", "订购", "buy", "price", "cost", "discount", "trial", "sign up",
        "signup", "download", "order", "coupon", "pricing", "purchase",
    ],
    "navigational": [
        "官网", "官方", "登录", "登陆", "客服", "首页", "官网入口", "login",
        "log in", "sign in", "official", "homepage", "website", "dashboard",
    ],
}

# 意图 → 内容类型 / schema / 战术
_PLAYBOOK = {
    "informational": {
        "content_type": "指南 / How-to 长文",
        "schema": ["Article", "FAQPage", "HowTo"],
        "geo_seo": "答案前置 + 定义块 + 问句式 H2;GEO 最爱被引的就是这类自包含解释",
    },
    "commercial": {
        "content_type": "对比 / 评测 / 榜单页",
        "schema": ["ItemList", "Product", "Review"],
        "geo_seo": "上 ItemList + 对比表,命中'最好的 X';铺 G2/知乎/Reddit 第三方背书,AI 在这类查询里直接抽榜单",
    },
    "transactional": {
        "content_type": "产品 / 落地页",
        "schema": ["Product", "Offer", "Organization"],
        "geo_seo": "Product schema 带价格 + 清晰 CTA + 信任信号;SEO 重于 GEO,但价格/规格要可被抽取",
    },
    "navigational": {
        "content_type": "品牌 / 官网页",
        "schema": ["Organization", "WebSite", "BreadcrumbList"],
        "geo_seo": "Organization + sameAs 实体可信链,确保品牌词查询命中你而非仿冒/竞品",
    },
}


def _match(sig, q):
    """英文信号用词边界(避免 whichever→which、reorder→order),中文用子串。"""
    sl = sig.lower()
    if re.match(r"^[a-z0-9 .'-]+$", sl):
        return re.search(r"\b" + re.escape(sl) + r"\b", q) is not None
    return sl in q


def classify(query, lang="auto"):
    """返回意图分类 + 内容类型映射 + 战术。"""
    q = (query or "").lower()
    scores = {}
    hits = {}
    for intent, sigs in _SIGNALS.items():
        matched = [s for s in sigs if _match(s, q)]
        scores[intent] = len(matched)
        hits[intent] = matched
    # 取最高分;并列时按 商业 > 交易 > 信息 > 导航 的商业价值优先
    order = ["commercial", "transactional", "informational", "navigational"]
    best = max(order, key=lambda i: (scores[i], -order.index(i)))
    if scores[best] == 0:
        best = "informational"  # 无信号默认信息型
        confidence = "low"
    elif scores[best] >= 2:
        confidence = "high"
    else:
        confidence = "medium"
    pb = _PLAYBOOK[best]
    return {
        "query": query,
        "intent": best,
        "confidence": confidence,
        "signals_matched": hits[best],
        "all_scores": scores,
        "content_type": pb["content_type"],
        "recommended_schema": pb["schema"],
        "geo_seo_tactic": pb["geo_seo"],
        "note": "信号不足,意图判断仅供参考,建议人工确认" if confidence == "low" else "",
    }


def render(result):
    out = ["# 搜索意图分类: %s" % result["query"], ""]
    out.append("意图: **%s**(置信度 %s)" % (result["intent"], result["confidence"]))
    if result["signals_matched"]:
        out.append("命中信号: %s" % "、".join(result["signals_matched"]))
    out.append("内容类型: %s" % result["content_type"])
    out.append("该上 schema: %s" % "、".join(result["recommended_schema"]))
    out.append("GEO/SEO 战术: %s" % result["geo_seo_tactic"])
    if result.get("note"):
        out.append("⚠️ %s" % result["note"])
    return "\n".join(out)
