"""报告渲染 + 批量站点审计。

- batch_score: 批量给多页打分,弱页优先排序
- to_html: 单页评分 -> 自包含 HTML 报告
- to_sarif: 失分项 -> SARIF(接 GitHub Code Scanning)
纯标准库。
"""

import html as _html
import json

from . import htmldoc, scoring


def batch_score(paths, robots_text=None, llms_text=None, market="auto"):
    rows = []
    for p in paths:
        try:
            doc = htmldoc.from_file(p)
            r = scoring.score_document(doc, robots_text=robots_text,
                                       llms_text=llms_text, market=market)
            rows.append({"path": p, "score": r["score"], "grade": r["grade"],
                         "geo_score": r["geo_score"], "seo_score": r["seo_score"],
                         "vetoes": r["vetoes"], "weakest": r["weakest"]})
        except Exception as e:  # noqa
            rows.append({"path": p, "score": None, "grade": "错误", "error": str(e)})
    rows.sort(key=lambda x: (x["score"] is not None, x["score"] if x["score"] is not None else 0))
    return {"count": len(rows), "pages": rows,
            "avg_score": round(sum(x["score"] for x in rows if x["score"] is not None)
                               / max(1, len([x for x in rows if x["score"] is not None])), 1)}


def to_html(result, title="HeiGe-GEO-SEO 评分报告"):
    e = _html.escape
    grade_color = {"优": "#1a9850", "良": "#66bd63", "待优化": "#fdae61", "危急": "#d73027"}
    rows = []
    for d in result["dimensions"]:
        rows.append('<tr><td><b>[%s] %s</b></td><td>%.1f / %d</td><td></td></tr>'
                    % (e(d["key"]), e(d["name"]), d["earned"], d["weight_evaluated"]))
        for c in d["checks"]:
            mark = {"pass": "✅", "partial": "🟡", "fail": "❌", "unknown": "❔"}[c["status"]]
            rows.append('<tr><td style="padding-left:20px">%s %s</td><td>%.1f / %d</td><td>%s</td></tr>'
                        % (mark, e(c["name"]), c["earned"], c["weight"], e(c["note"])))
    vet = ""
    if result["vetoes"]:
        vet = "<div class='veto'><b>否决项(总分封顶 60):</b><ul>" + \
              "".join("<li>%s</li>" % e(v) for v in result["vetoes"]) + "</ul></div>"
    return """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title><style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:820px;margin:24px auto;color:#222}
.score{font-size:48px;font-weight:700;color:%s}
table{border-collapse:collapse;width:100%%;margin-top:16px}
td{border-bottom:1px solid #eee;padding:6px 8px;font-size:14px}
.veto{background:#fff3f3;border:1px solid #f5c6cb;padding:12px;border-radius:6px;margin-top:16px}
.sub{color:#666}
</style></head><body>
<h1>%s</h1>
<div class="score">%d<span style="font-size:20px">/100 · %s</span></div>
<p class="sub">市场: %s · GEO 分: %s · SEO 分: %s</p>
%s
<table>%s</table>
<p class="sub">由 HeiGe-GEO-SEO 生成</p>
</body></html>""" % (
        e(title), grade_color.get(result["grade"], "#666"), e(title),
        result["score"], e(result["grade"]), e(result["market"]),
        result["geo_score"], result["seo_score"], vet, "".join(rows))


def to_sarif(result, page_uri="page.html"):
    """把失分/部分达标项渲染成 SARIF 2.1.0(GitHub Code Scanning 可读)。"""
    rules = []
    results = []
    seen_rules = set()
    for d in result["dimensions"]:
        for c in d["checks"]:
            if c["status"] in ("pass", "unknown"):
                continue
            rule_id = "GEO-%s" % c["id"]
            if rule_id not in seen_rules:
                seen_rules.add(rule_id)
                rules.append({"id": rule_id, "name": c["name"],
                              "shortDescription": {"text": c["name"]}})
            level = "error" if c["status"] == "fail" else "warning"
            results.append({
                "ruleId": rule_id,
                "level": level,
                "message": {"text": "%s (%.1f/%d) %s" % (c["name"], c["earned"],
                                                         c["weight"], c["note"])},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": page_uri}}}],
            })
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {"name": "HeiGe-GEO-SEO", "version": "1.1.0",
                                "rules": rules}},
            "results": results,
        }],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2) + "\n"


def batch_to_html(batch, title="HeiGe-GEO-SEO 批量审计"):
    e = _html.escape
    rows = []
    for p in batch["pages"]:
        sc = "错误" if p["score"] is None else str(p["score"])
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(p["path"]), sc, e(p.get("grade", ""))))
    return """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title><style>body{font-family:sans-serif;max-width:820px;margin:24px auto}
table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid #eee;padding:6px;text-align:left}
</style></head><body><h1>%s</h1><p>共 %d 页,平均分 %s。弱页优先:</p>
<table><tr><th>页面</th><th>分数</th><th>档位</th></tr>%s</table></body></html>""" % (
        e(title), e(title), batch["count"], batch["avg_score"], "".join(rows))
