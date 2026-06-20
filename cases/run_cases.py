#!/usr/bin/env python3
"""跑通所有案例:对每个 case 做 基线打分 -> 生成 robots/schema/llms ->
注入 schema 后复评 -> 写 output/ 与 SUMMARY.md。

用法:
  python3 run_cases.py              # 跑全部案例
  python3 run_cases.py case-01-saas-landing   # 只跑一个
零依赖,仅标准库。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lib import htmldoc, scoring, generators  # noqa: E402


def render_score(result):
    lines = []
    lines.append("市场: %s   总分: %d/100 (%s)   GEO: %s   SEO: %s" % (
        result["market"], result["score"], result["grade"],
        result["geo_score"], result["seo_score"]))
    for d in result["dimensions"]:
        lines.append("  [%s] %s  %.1f/%d" % (d["key"], d["name"], d["earned"],
                                             d["weight_evaluated"]))
    if result["vetoes"]:
        lines.append("  否决项: " + "; ".join(result["vetoes"]))
    return "\n".join(lines)


def build_schema(cfg):
    t = cfg["type"]
    if t == "faqpage":
        node = generators.gen_faqpage([(q, a) for q, a in cfg["qa"]])
    elif t == "product":
        node = generators.gen_product(
            name=cfg["name"], description=cfg.get("description", ""),
            brand=cfg.get("brand"), price=cfg.get("price"),
            currency=cfg.get("currency", "CNY"), rating=cfg.get("rating"),
            rating_count=cfg.get("rating_count"))
    elif t == "article":
        node = generators.gen_article(
            title=cfg["title"], description=cfg.get("description", ""),
            author=cfg.get("author"), org=cfg.get("org"), url=cfg.get("url"),
            date_published=cfg.get("date_published"),
            author_url=cfg.get("author_url"), same_as=cfg.get("same_as"))
    else:
        raise ValueError("unknown schema type %s" % t)
    return node


def inject_schema(html, script):
    if "</head>" in html:
        return html.replace("</head>", script + "\n</head>", 1)
    if "<body>" in html:
        return html.replace("<body>", "<body>\n" + script, 1)
    return script + "\n" + html


def run_case(case_dir):
    with open(os.path.join(case_dir, "case.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    out = os.path.join(case_dir, "output")
    os.makedirs(out, exist_ok=True)

    input_path = os.path.join(case_dir, cfg["input"])
    html = open(input_path, encoding="utf-8").read()
    market = cfg.get("market", "auto")

    # 1) baseline
    before = scoring.score_document(htmldoc.from_string(html), market=market)
    with open(os.path.join(out, "score-before.txt"), "w", encoding="utf-8") as fh:
        fh.write(render_score(before) + "\n")

    # 2) generate artifacts
    robots = generators.gen_robots(cfg["robots_strategy"], sitemap=cfg.get("sitemap"))
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots)

    schema_node = build_schema(cfg["schema"])
    schema_script = generators.to_script(schema_node)
    with open(os.path.join(out, "schema.html"), "w", encoding="utf-8") as fh:
        fh.write(schema_script + "\n")

    llms_cfg = cfg["llms"]
    sections = [{"title": "Docs", "links": [
        {"name": n, "url": u, "desc": d} for u, n, d in llms_cfg["links"]]}]
    llms = generators.gen_llms_txt(llms_cfg["site"], llms_cfg["summary"], sections=sections)
    with open(os.path.join(out, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(llms)

    # 3) optimized page = input + injected schema
    optimized = inject_schema(html, schema_script)
    with open(os.path.join(out, "optimized.html"), "w", encoding="utf-8") as fh:
        fh.write(optimized)

    # 4) re-score with optimized page + robots + llms
    after = scoring.score_document(htmldoc.from_string(optimized),
                                   robots_text=robots, llms_text=llms, market=market)
    with open(os.path.join(out, "score-after.txt"), "w", encoding="utf-8") as fh:
        fh.write(render_score(after) + "\n")

    # 5) summary
    summary = build_summary(cfg, before, after)
    with open(os.path.join(out, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write(summary)

    return {"name": cfg["name"], "before": before["score"], "after": after["score"],
            "before_grade": before["grade"], "after_grade": after["grade"]}


def build_summary(cfg, before, after):
    s = []
    s.append("# %s · 优化总结\n" % cfg["name"])
    s.append("> %s\n" % cfg["scenario"])
    s.append("## 评分变化\n")
    s.append("| 维度 | 优化前 | 优化后 |")
    s.append("|---|---|---|")
    s.append("| 总分 | %d/100 (%s) | %d/100 (%s) |" % (
        before["score"], before["grade"], after["score"], after["grade"]))
    s.append("| GEO 分 | %s | %s |" % (before["geo_score"], after["geo_score"]))
    s.append("| SEO 分 | %s | %s |" % (before["seo_score"], after["seo_score"]))
    s.append("")
    s.append("提升 **%d 分**(%s → %s)。\n" % (
        after["score"] - before["score"], before["grade"], after["grade"]))
    s.append("## 目标 AI 引擎\n")
    s.append("、".join(cfg.get("target_engines", [])) + "\n")
    s.append("## 做了什么\n")
    s.append("- robots.txt 策略:`%s`" % cfg["robots_strategy"])
    s.append("- 结构化数据:`%s` JSON-LD(见 schema.html,已注入 optimized.html)" % cfg["schema"]["type"])
    s.append("- llms.txt:B2A 入口(见 llms.txt)")
    s.append("")
    s.append("## 发布建议(按目标引擎)\n")
    if cfg.get("market") == "cn":
        s.append("国内押生态多平铺:**知乎(最高 ROI)+ 微信公众号(元宝独家)+ 百家号(文心)+ 今日头条(豆包)**。")
        s.append("一稿四态:深度长文、知乎问答体、小红书短图文、视频带字幕。详见知识库 03-publishing-channels。")
    else:
        s.append("海外押 Reddit + Wikipedia,官网上结构化数据作事实锚点,有 API 文档做 llms.txt 给 agent 用户。")
    s.append("")
    s.append("## 最该先修的项\n")
    for w in after["weakest"][:3]:
        s.append("- %s/%s %s(%.1f/%d)%s" % (w["dim"], w["id"], w["name"],
                                            w["earned"], w["weight"],
                                            " · " + w["note"] if w["note"] else ""))
    s.append("")
    return "\n".join(s)


def main(argv):
    targets = []
    if argv:
        targets = [os.path.join(HERE, a) for a in argv]
    else:
        for name in sorted(os.listdir(HERE)):
            p = os.path.join(HERE, name)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "case.json")):
                targets.append(p)

    results = []
    for t in targets:
        if not os.path.isfile(os.path.join(t, "case.json")):
            print("跳过(无 case.json): %s" % t)
            continue
        r = run_case(t)
        results.append(r)
        print("%-18s  %d (%s) -> %d (%s)" % (
            os.path.basename(t), r["before"], r["before_grade"],
            r["after"], r["after_grade"]))

    # aggregate RESULTS.md
    lines = ["# 案例集运行结果\n", "| 案例 | 优化前 | 优化后 | 提升 |", "|---|---|---|---|"]
    for r in results:
        lines.append("| %s | %d (%s) | %d (%s) | +%d |" % (
            r["name"], r["before"], r["before_grade"], r["after"],
            r["after_grade"], r["after"] - r["before"]))
    lines.append("")
    with open(os.path.join(HERE, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("\n写入 cases/RESULTS.md")
    # all cases should show improvement
    ok = all(r["after"] >= r["before"] for r in results)
    return 0 if ok and results else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
