"""内链 / 孤儿页审计(站点级)。

孤儿页(没有任何内链指向)拿不到内部权重传导,AI 也难理解站点拓扑。
内链既是 SEO 也是 GEO 信号(帮 AI 理解站点结构)。这里吃多页 HTML,建内链图,
找孤儿页、零出链页、统计内链分布。纯标准库。
"""

import posixpath
import re

from . import htmldoc

# 除 http(s) 外的 URL scheme(mailto:/javascript:/tel: 等),一律非站内
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _strip_www(host):
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def _norm(href, base_hosts, base="/"):
    """把 href 规范成站内 path;非站内或无法判定返回 None。
    base 是当前页路径,供相对链接解析。"""
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return None
    m = re.match(r"(?:https?:)?//([^/?#]+)(/[^?#]*)?", href, re.IGNORECASE)
    if m:
        # 绝对 URL 与协议相对 //host/path 同待遇:host 必须在 base_hosts 里才算站内,
        # 不传 base_hosts 时带域名的链接无法判定,一律不计
        host = _strip_www(m.group(1).split(":")[0])
        if host not in base_hosts:
            return None
        path = m.group(2) or "/"
    elif _SCHEME.match(href):
        return None  # 非 http 协议
    elif href.startswith("/"):
        path = href.split("?")[0].split("#")[0]
    else:
        # 相对链接:基于当前页路径解析成站内绝对 path,否则相对互链的站会全报孤儿
        rel = href.split("?")[0].split("#")[0]
        if not rel:
            return None
        base_dir = base if base.endswith("/") else posixpath.dirname(base)
        path = posixpath.normpath(posixpath.join(base_dir or "/", rel))
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
        # 相对链接解析基准保留原始路径的结尾斜杠(目录页语义),别用剥过的 key
        base = path.split("?")[0].split("#")[0]
        if "://" in base:
            base = re.sub(r"^https?://[^/]+", "", base, flags=re.IGNORECASE) or "/"
        outs = set()
        for lk in doc.links:
            t = _norm(lk.get("href", ""), base_hosts, base=base)
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
                "传 base_hosts 才能判带域名的绝对链接为站内,不传则带域名的链接一律不计;"
                "相对链接已按当前页路径解析成站内 path。",
    }
