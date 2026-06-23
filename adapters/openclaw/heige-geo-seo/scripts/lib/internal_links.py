"""内链 / 孤儿页审计(站点级)。

孤儿页(没有任何内链指向)拿不到内部权重传导,AI 也难理解站点拓扑。
内链既是 SEO 也是 GEO 信号(帮 AI 理解站点结构)。这里吃多页 HTML,建内链图,
找孤儿页、零出链页、统计内链分布。纯标准库。
"""

import re

from . import htmldoc


def _strip_www(host):
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def _norm(href, base_hosts):
    """把 href 规范成站内 path;非站内返回 None。"""
    href = (href or "").strip()
    if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
        return None
    m = re.match(r"https?://([^/]+)(/[^?#]*)?", href, re.IGNORECASE)
    if m:
        host = _strip_www(m.group(1))
        if base_hosts and host not in base_hosts:
            return None  # 外站
        path = m.group(2) or "/"
    elif href.startswith("/"):
        path = href.split("?")[0].split("#")[0]
    else:
        return None  # 相对路径或外链,跳过
    path = path.rstrip("/") or "/"
    return path


def _page_key(path):
    p = path.split("?")[0].split("#")[0]
    if "://" in p:
        p = re.sub(r"^https?://[^/]+", "", p)
    return (p.rstrip("/") or "/")


def analyze(pages, base_hosts=None, home="/"):
    """pages: list of (path_or_url, HtmlDoc|html_str)。
    注意:pages 的 key 用 URL path(如 /about)而非本地文件名(about.html),
    否则与 HTML 里的 /about 内链对不上会全报孤儿;且应喂全站或至少所有入口页。"""
    base_hosts = set(_strip_www(h) for h in (base_hosts or []))
    known = {}
    outbound = {}
    for path, p in pages:
        doc = p if hasattr(p, "links") else htmldoc.from_string(p)
        key = _page_key(path)
        known[key] = doc
        outs = set()
        for lk in doc.links:
            t = _norm(lk.get("href", ""), base_hosts)
            if t is not None and t != key:
                outs.add(t)
        outbound[key] = outs

    inbound = {k: 0 for k in known}
    for src, outs in outbound.items():
        for dst in outs:
            if dst in inbound:
                inbound[dst] += 1

    home_key = _page_key(home)
    orphans = [k for k in known if inbound[k] == 0 and k != home_key]
    no_outbound = [k for k in known if not outbound[k]]
    total_links = sum(len(o) for o in outbound.values())
    return {
        "pages": len(known),
        "internal_links_total": total_links,
        "avg_internal_links": round(total_links / len(known), 1) if known else 0,
        "orphan_pages": sorted(orphans),
        "orphan_count": len(orphans),
        "pages_no_outbound": sorted(no_outbound),
        "inbound_by_page": dict(sorted(inbound.items(), key=lambda kv: kv[1])),
        "verdict": "有孤儿页/内链缺口" if orphans or no_outbound else "内链结构健康",
        "note": "孤儿页(0 内链指向)拿不到权重传导,给它们加入口链接;"
                "传 base_hosts 才能判带域名的绝对链接为站内。",
    }
