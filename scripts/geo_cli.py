#!/usr/bin/env python3
"""HeiGe-GEO-SEO unified CLI.

Subcommands:
  score   给一个 HTML 文件打 GEO 可被引用度分(6 维 22 项)
  robots  生成 AI 爬虫 robots.txt(allow-all / expose-only / cn-index)
  schema  生成 JSON-LD 结构化数据(article / faqpage / howto / product)
  llms    生成 llms.txt

零依赖,仅 Python 标准库。示例见 `python3 geo_cli.py <cmd> --help`。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import htmldoc, scoring, generators  # noqa: E402


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _emit(text, out):
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        print("写入 %s" % out)
    else:
        print(text)


# --------------------------------------------------------------------------
# score
# --------------------------------------------------------------------------
def cmd_score(args):
    doc = htmldoc.from_string(_read(args.input))
    robots_text = _read(args.robots) if args.robots else None
    llms_text = _read(args.llms) if args.llms else None
    result = scoring.score_document(
        doc, robots_text=robots_text, llms_text=llms_text,
        llms_full=args.llms_full, ai_txt=args.ai_txt, market=args.market)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["score"] >= args.fail_under else 1

    print("=" * 56)
    print("HeiGe-GEO-SEO 评分报告  |  市场: %s" % result["market"])
    print("=" * 56)
    print("总分: %d / 100   档位: %s" % (result["score"], result["grade"]))
    if result["geo_score"] is not None:
        print("GEO 分(被 AI 引用就绪度): %s" % result["geo_score"])
    if result["seo_score"] is not None:
        print("SEO 分(被搜索排名就绪度): %s" % result["seo_score"])
    print("-" * 56)
    for d in result["dimensions"]:
        print("[%s] %s  %.1f/%d" % (d["key"], d["name"], d["earned"], d["weight_evaluated"]))
        for c in d["checks"]:
            mark = {"pass": "OK ", "partial": "~  ", "fail": "X  ", "unknown": "?  "}[c["status"]]
            line = "   %s%s  %.1f/%d" % (mark, c["name"], c["earned"], c["weight"])
            if c["note"]:
                line += "  (%s)" % c["note"]
            print(line)
    if result["vetoes"]:
        print("-" * 56)
        print("否决项(总分已封顶 60):")
        for v in result["vetoes"]:
            print("   ! " + v)
    print("-" * 56)
    print("最该先修的 5 项:")
    for w in result["weakest"]:
        print("   %s/%s %s  %.1f/%d  %s" % (w["dim"], w["id"], w["name"],
                                            w["earned"], w["weight"], w["note"]))
    print("=" * 56)
    return 0 if result["score"] >= args.fail_under else 1


# --------------------------------------------------------------------------
# robots
# --------------------------------------------------------------------------
def cmd_robots(args):
    text = generators.gen_robots(strategy=args.strategy, sitemap=args.sitemap,
                                 disallow_paths=args.disallow or None)
    _emit(text, args.out)
    return 0


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------
def _split_pair(s, sep="::"):
    parts = s.split(sep, 1)
    if len(parts) != 2:
        raise ValueError("期望格式 A%sB,收到: %s" % (sep, s))
    return parts[0].strip(), parts[1].strip()


def cmd_schema(args):
    t = args.type
    if t == "article":
        node = generators.gen_article(
            title=args.title, description=args.description or "",
            author=args.author, org=args.org, url=args.url,
            date_published=args.date_published, date_modified=args.date_modified,
            author_url=args.author_url, same_as=args.same_as or None)
    elif t == "faqpage":
        pairs = [_split_pair(x) for x in (args.qa or [])]
        if args.qa_file:
            for line in _read(args.qa_file).splitlines():
                line = line.strip()
                if line and "::" in line:
                    pairs.append(_split_pair(line))
        if not pairs:
            print("faqpage 需要至少一组 --qa \"问题::答案\"", file=sys.stderr)
            return 2
        node = generators.gen_faqpage(pairs)
    elif t == "howto":
        steps = [_split_pair(x) for x in (args.step or [])]
        if not steps:
            print("howto 需要至少一个 --step \"步骤名::说明\"", file=sys.stderr)
            return 2
        node = generators.gen_howto(args.name, steps)
    elif t == "product":
        node = generators.gen_product(
            name=args.name, description=args.description or "", brand=args.brand,
            price=args.price, currency=args.currency, rating=args.rating,
            rating_count=args.rating_count)
    else:
        print("unknown schema type", file=sys.stderr)
        return 2

    text = generators.to_script(node) if not args.raw else json.dumps(
        node, ensure_ascii=False, indent=2)
    _emit(text, args.out)
    return 0


# --------------------------------------------------------------------------
# llms
# --------------------------------------------------------------------------
def cmd_llms(args):
    sections = []
    if args.links:
        links = generators.parse_links_file(_read(args.links))
        sections.append({"title": args.section, "links": links})
    body = None
    if args.body:
        body = args.body
    elif args.body_file:
        body = _read(args.body_file)
    text = generators.gen_llms_txt(args.site, args.summary, sections=sections, body=body)
    _emit(text, args.out)
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="geo_cli", description="HeiGe-GEO-SEO 工具集")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("score", help="给 HTML 打 GEO 可被引用度分")
    s.add_argument("--input", required=True, help="HTML 文件路径")
    s.add_argument("--robots", help="robots.txt 文件(纳入爬虫准入维度)")
    s.add_argument("--llms", help="llms.txt 文件(纳入发现文件维度)")
    s.add_argument("--llms-full", action="store_true", help="存在 llms-full.txt")
    s.add_argument("--ai-txt", action="store_true", help="存在 ai.txt")
    s.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    s.add_argument("--json", action="store_true", help="输出 JSON")
    s.add_argument("--fail-under", type=int, default=0, help="低于此分退出码 1(CI 用)")
    s.set_defaults(func=cmd_score)

    r = sub.add_parser("robots", help="生成 AI 爬虫 robots.txt")
    r.add_argument("--strategy", choices=["allow-all", "expose-only", "cn-index"],
                   default="allow-all")
    r.add_argument("--sitemap", help="sitemap URL")
    r.add_argument("--disallow", action="append", help="禁止路径,可多次")
    r.add_argument("--out", help="输出文件,默认打印")
    r.set_defaults(func=cmd_robots)

    sc = sub.add_parser("schema", help="生成 JSON-LD 结构化数据")
    sc.add_argument("--type", required=True,
                    choices=["article", "faqpage", "howto", "product"])
    sc.add_argument("--title")
    sc.add_argument("--name")
    sc.add_argument("--description")
    sc.add_argument("--author")
    sc.add_argument("--author-url")
    sc.add_argument("--same-as", action="append")
    sc.add_argument("--org")
    sc.add_argument("--url")
    sc.add_argument("--date-published")
    sc.add_argument("--date-modified")
    sc.add_argument("--qa", action="append", help='faqpage: "问题::答案",可多次')
    sc.add_argument("--qa-file", help="faqpage: 每行 问题::答案")
    sc.add_argument("--step", action="append", help='howto: "步骤名::说明",可多次')
    sc.add_argument("--brand")
    sc.add_argument("--price")
    sc.add_argument("--currency", default="CNY")
    sc.add_argument("--rating")
    sc.add_argument("--rating-count")
    sc.add_argument("--raw", action="store_true", help="只输出 JSON,不包 script 标签")
    sc.add_argument("--out")
    sc.set_defaults(func=cmd_schema)

    l = sub.add_parser("llms", help="生成 llms.txt")
    l.add_argument("--site", required=True, help="站点/产品名")
    l.add_argument("--summary", required=True, help="一句话简介")
    l.add_argument("--links", help="链接文件,每行 url | 名称 | 描述")
    l.add_argument("--section", default="Docs", help="链接分节标题")
    l.add_argument("--body", help="可选自由说明段落")
    l.add_argument("--body-file", help="可选自由说明段落文件")
    l.add_argument("--out")
    l.set_defaults(func=cmd_llms)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
