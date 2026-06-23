"""关键词蚕食(cannibalization)检测:多页抢同一个词,优化越多越互相打架。

SEO 多页站点的硬伤,工具能批量打分却看不出页面间关系。这里做跨页的
title/H1/关键词重叠检测,标出冲突对。纯标准库,站点级(吃多页)。
"""

import re

from . import htmldoc


_STOP = set("的 了 和 与 是 在 你 我 他 它 们 个 这 那 一 有 为 之 上 下 the a an of to "
            "and or for in on with is are how what why best top guide".split())


def _keywords(doc):
    """从 title + 标题层抽关键词集(去停用词、短词)。"""
    text = (doc.title + " " + " ".join(t for _, t in doc.headings)).lower()
    toks = re.findall(r"[a-z0-9]+|[〇㐀-䶿一-鿿]{2,4}", text)
    return set(t for t in toks if t not in _STOP and len(t) >= 2)


def _h1(doc):
    h1 = [t for lvl, t in doc.headings if lvl == 1]
    return h1[0].strip().lower() if h1 else ""


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def analyze(pages, threshold=0.5):
    """pages: list of (path, HtmlDoc) 或 (path, html_str)。找蚕食冲突对。"""
    docs = []
    for path, p in pages:
        doc = p if hasattr(p, "headings") else htmldoc.from_string(p)
        docs.append({"path": path, "title": doc.title.strip().lower(),
                     "h1": _h1(doc), "kw": _keywords(doc)})
    conflicts = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            kw_sim = _jaccard(a["kw"], b["kw"])
            title_same = a["title"] and a["title"] == b["title"]
            h1_same = a["h1"] and a["h1"] == b["h1"]
            if kw_sim >= threshold or title_same or h1_same:
                reasons = []
                if title_same:
                    reasons.append("title 完全相同")
                if h1_same:
                    reasons.append("H1 完全相同")
                if kw_sim >= threshold:
                    reasons.append("关键词重叠 %.0f%%" % (kw_sim * 100))
                conflicts.append({
                    "page_a": a["path"], "page_b": b["path"],
                    "kw_overlap": round(kw_sim, 2), "reasons": reasons,
                    "fix": "两页抢同一意图:合并、或差异化定位(一页打主词一页打长尾)、加 canonical 指向主页",
                })
    conflicts.sort(key=lambda c: c["kw_overlap"], reverse=True)
    return {
        "pages_checked": len(docs),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "verdict": "有蚕食风险" if conflicts else "未检出明显蚕食",
        "note": "这是 title/H1/关键词的静态重叠启发式,非 GSC 数据驱动:会漏掉'标题不同但"
                "搜索意图相同'的蚕食,也无 impression/position 严重度分级。完整蚕食审计需 GSC "
                "的 {query, page} 配对数据(v1.6 backlog)。阈值默认 0.5。",
    }
