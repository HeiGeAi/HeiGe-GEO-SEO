#!/usr/bin/env python3
"""HeiGe-GEO-SEO unified CLI.

诊断:
  score      给 HTML 打 GEO 可被引用度分(6 维 22 项)
  diagnose   「为何没被引用」7 根因诊断
  agentready WebMCP / agent 任务就绪静态审计
  batch      批量站点审计,弱页优先
  report     评分渲染成 HTML / SARIF
产出:
  rewrite    改写指令编译器(吃打分→出可喂任意 LLM 的改写指令包)
  brief      GEO Content Brief 生成器
度量:
  prompts    buyer prompt 集生成器(意图问句,中英双语)
  sov        Share of Voice 度量(三公式+基准阈值+采样置信度)
生成:
  robots / schema / llms / files / attribution

零依赖,仅 Python 标准库。示例见 `python3 geo_cli.py <cmd> --help`。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import (htmldoc, scoring, generators, instruction, prompts as promptlib,  # noqa: E402
                 sov as sovlib, diagnose as diaglib, report as reportlib,
                 attribution, agent_readiness, anti_ai,
                 platform_recommend as recommendlib, intent as intentlib,
                 factcheck as fclib, lostprompt as lplib, cannibalize as canlib,
                 internal_links as illib, cwv as cwvlib, token_budget as tblib,
                 content_engineering as celib, sourcing as sourcinglib,
                 playbook as playbooklib, measure as measurelib)


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


def _split_opt(s, sep="::"):
    """容忍 url 缺省:'名称::url' 或仅 '名称' -> (名称, url|None)。"""
    if sep in s:
        name, url = s.split(sep, 1)
        return (name.strip(), url.strip())
    return (s.strip(), None)


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
    elif t == "organization":
        node = generators.gen_organization(
            name=args.name or args.org, url=args.url, logo=args.logo,
            same_as=args.same_as or None, founder=args.founder,
            description=args.description or "")
    elif t == "person":
        node = generators.gen_person(
            name=args.name or args.author, job_title=args.job_title, url=args.url,
            knows_about=args.knows_about or None, same_as=args.same_as or None,
            works_for=args.org)
    elif t == "website":
        node = generators.gen_website(
            name=args.name, url=args.url, publisher=args.org)
    elif t == "breadcrumb":
        items = [_split_opt(x) for x in (args.item or [])]
        if not items:
            print("breadcrumb 需要 --item \"名称::url\"(末项 url 可空),可多次", file=sys.stderr)
            return 2
        node = generators.gen_breadcrumb(items)
    elif t == "itemlist":
        items = [_split_opt(x) for x in (args.item or [])]
        if not items:
            print("itemlist 需要 --item \"名称::url\",可多次", file=sys.stderr)
            return 2
        node = generators.gen_itemlist(args.name or args.title or "List", items)
    elif t == "review":
        if not (args.name and args.rating and args.author):
            print("review 需要 --name(被评对象)--rating --author", file=sys.stderr)
            return 2
        node = generators.gen_review(args.name, args.rating, args.author,
                                     body=args.description or "")
    elif t == "action":
        if not (args.action and args.url):
            print("action 需要 --action(order/reserve/search/subscribe/register)和 --url", file=sys.stderr)
            return 2
        node = generators.gen_action(args.action, args.url, name=args.name,
                                     entity_name=args.org)
    elif t == "speakable":
        if not args.selector:
            print("speakable 需要 --selector(CSS 选择器,可多次)", file=sys.stderr)
            return 2
        node = generators.gen_speakable(args.selector)
    elif t == "software":
        if not args.name:
            print("software 需要 --name", file=sys.stderr)
            return 2
        node = generators.gen_software_application(
            args.name, price=args.price, currency=args.currency,
            rating=args.rating, rating_count=args.rating_count)
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
# rewrite (改写指令编译器)
# --------------------------------------------------------------------------
def cmd_rewrite(args):
    doc = htmldoc.from_string(_read(args.input))
    score = scoring.score_document(doc, market=args.market)
    pack = instruction.compile_instructions(score, target_engine=args.engine,
                                            lang=args.lang)
    if args.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        _emit(instruction.render_markdown(pack), args.out)
    return 0


def cmd_brief(args):
    sections = args.section or []
    intent_res = None
    if args.intent or args.topic:
        intent_res = intentlib.classify(args.intent or args.question or args.topic)
    brief = instruction.gen_geo_brief(
        topic=args.topic, primary_question=args.question or args.topic,
        sections=sections, entities=args.entity or None,
        paa_questions=args.paa or None, target_engine=args.engine,
        lang=args.lang)
    if intent_res:
        brief["search_intent"] = {
            "intent": intent_res["intent"], "confidence": intent_res["confidence"],
            "content_type": intent_res["content_type"],
            "recommended_schema": intent_res["recommended_schema"],
            "tactic": intent_res["geo_seo_tactic"],
        }
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        md = instruction.render_brief_markdown(brief)
        if intent_res:
            md = intentlib.render(intent_res) + "\n\n---\n\n" + md
        _emit(md, args.out)
    return 0


def cmd_prompts(args):
    rows = promptlib.generate(
        brand=args.brand, category=args.category,
        competitors=args.competitor or None, problems=args.problem or None,
        personas=args.persona or None, geographies=args.geo or None,
        usecases=args.usecase or None, lang=args.lang, limit=args.limit)
    meta = {"brand": args.brand, "category": args.category, "lang": args.lang}
    if args.csv:
        _emit(promptlib.to_csv(rows), args.out)
    else:
        text = promptlib.to_json(rows, meta)
        _emit(text.rstrip("\n"), args.out)
    return 0


def cmd_sov(args):
    records = json.loads(_read(args.input))
    if isinstance(records, dict):
        records = records.get("records", [])
    aliases = json.loads(_read(args.aliases)) if args.aliases else None
    comp_domains = json.loads(_read(args.competitor_domains)) if args.competitor_domains else None
    result = sovlib.analyze(
        records, brand=args.brand, competitors=args.competitor or None,
        aliases=aliases, brand_domain=args.brand_domain,
        competitor_domains=comp_domains)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnose(args):
    doc = htmldoc.from_string(_read(args.input))
    result = diaglib.diagnose(doc, market=args.market)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print("「为何没被引用」诊断  市场: %s  裁决: %s" % (result["market"], result["verdict"]))
    print("-" * 56)
    for f in result["findings"]:
        mark = {"pass": "OK ", "fail": "X  ", "warn": "!  ", "manual": "?  "}[f["status"]]
        line = "%s%s" % (mark, f["cause"])
        if f["fix"]:
            line += "\n     修复: " + f["fix"]
        print(line)
    return 0 if result["failed_count"] == 0 else 1


def cmd_agentready(args):
    doc = htmldoc.from_string(_read(args.input))
    result = agent_readiness.audit(doc)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print("WebMCP / agent 就绪审计  分数: %d/100 (%s)  表单数: %d" % (
        result["score"], result["grade"], result["form_count"]))
    for c in result["checks"]:
        mark = "OK " if c["status"] == "pass" else "X  "
        line = "  %s%s (%d)" % (mark, c["name"], c["weight"])
        if c["fix"]:
            line += "\n     " + c["fix"]
        print(line)
    return 0


def cmd_batch(args):
    batch = reportlib.batch_score(args.inputs, market=args.market)
    if args.html:
        _emit(reportlib.batch_to_html(batch), args.html)
    print(json.dumps({"count": batch["count"], "avg_score": batch["avg_score"],
                      "pages": [{"path": p["path"], "score": p["score"],
                                 "grade": p.get("grade")} for p in batch["pages"]]},
                     ensure_ascii=False, indent=2))
    return 0 if batch["avg_score"] >= args.fail_under else 1


def cmd_report(args):
    doc = htmldoc.from_string(_read(args.input))
    robots_text = _read(args.robots) if args.robots else None
    llms_text = _read(args.llms) if args.llms else None
    result = scoring.score_document(doc, robots_text=robots_text,
                                    llms_text=llms_text, market=args.market)
    if args.format == "sarif":
        text = reportlib.to_sarif(result, page_uri=args.input)
    else:
        text = reportlib.to_html(result)
    _emit(text, args.out)
    return 0


def cmd_files(args):
    """生成一组 AI 发现/答案文件到目录。"""
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    written = []

    def w(name, content):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(name)

    w("ai.txt", generators.gen_ai_txt(allow_train=args.allow_train))
    w("robots.patch", generators.gen_robots_patch(allow_train=args.allow_train))
    w("humans.txt", generators.gen_humans_txt(
        team=[("CTO", args.author or "Team")], site=args.site,
        standards=["HTML5", "JSON-LD", "llms.txt"], last_update=args.date))
    if args.url:
        w("sitemap.xml", generators.gen_sitemap([(args.url, args.date)]))
        w("feed.xml", generators.gen_feed_xml(
            args.site or "Site", args.url,
            [("最新内容", args.date or "Sat, 21 Jun 2026 00:00:00 GMT", args.url)]))
    print("生成 %d 个文件到 %s: %s" % (len(written), out_dir, ", ".join(written)))
    return 0


def cmd_attribution(args):
    if args.log:
        result = attribution.parse_access_log(_read(args.log))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _emit(attribution.render_kit(site_url=args.url), args.out)
    return 0


def cmd_recommend(args):
    if args.reverse:
        result = recommendlib.reverse(args.reverse)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("平台「%s」能喂的 AI 引擎(%d 个):" % (
                result["platform"], result["engine_count"]))
            for f in result["feeds_engines"]:
                print("  %s  权重%d  [%s] %s" % (f["engine"], f["weight"],
                                               f["source"], f["why"]))
        return 0
    if not args.engine:
        print("需要 --engine(可多次,或 cn-all / overseas-all)或 --reverse 平台名",
              file=sys.stderr)
        return 2
    result = recommendlib.recommend(args.engine, content_type=args.content_type,
                                    top=args.top)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _emit(recommendlib.render_markdown(result), args.out)
    return 0


def cmd_intent(args):
    result = intentlib.classify(args.query)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _emit(intentlib.render(result), args.out)
    return 0


def cmd_baidu_push(args):
    urls = list(args.url or [])
    if args.url_file:
        urls += [ln.strip() for ln in _read(args.url_file).splitlines() if ln.strip()]
    if not urls:
        print("需要 --url(可多次)或 --url-file", file=sys.stderr)
        return 2
    text = generators.gen_baidu_push(args.site, args.token or "你的TOKEN", urls,
                                     fast=args.fast)
    _emit(text, args.out)
    return 0


def cmd_hreflang(args):
    locales = [_split_pair(x) for x in (args.locale or [])]
    if not locales:
        print("需要 --locale \"zh-CN::url\",可多次", file=sys.stderr)
        return 2
    text = generators.gen_hreflang(locales, x_default=args.x_default)
    _emit(text, args.out)
    return 0


def cmd_factcheck(args):
    records = json.loads(_read(args.input))
    if isinstance(records, dict):
        records = records.get("records", [])
    facts = json.loads(_read(args.facts))
    aliases = json.loads(_read(args.aliases)) if args.aliases else None
    result = fclib.check(records, args.brand, facts, aliases=aliases)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(fclib.render(result))
    return 0 if result["conflict_count"] == 0 else 1


def cmd_lostprompt(args):
    records = json.loads(_read(args.input))
    if isinstance(records, dict):
        records = records.get("records", [])
    aliases = json.loads(_read(args.aliases)) if args.aliases else None
    result = lplib.analyze(records, args.brand, args.competitor or [], aliases=aliases)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _emit(lplib.render(result), args.out)
    return 0


def cmd_cannibalize(args):
    pages = [(p, _read(p)) for p in args.inputs]
    result = canlib.analyze(pages, threshold=args.threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["conflict_count"] == 0 else 1


def cmd_internallinks(args):
    pages = [(p, _read(p)) for p in args.inputs]
    result = illib.analyze(pages, base_hosts=args.host or None, home=args.home)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["orphan_count"] == 0 else 1


def cmd_cwv(args):
    if args.psi:
        psi = json.loads(_read(args.psi))
        metrics = psi  # 期望 {lcp,inp,cls}
    else:
        metrics = {}
        if args.lcp is not None:
            metrics["lcp"] = args.lcp
        if args.inp is not None:
            metrics["inp"] = args.inp
        if args.cls is not None:
            metrics["cls"] = args.cls
    result = cwvlib.assess(metrics)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_token(args):
    text = _read(args.input) if args.input else (args.text or "")
    if args.budget:
        result = tblib.check(text, args.budget)
    else:
        result = {"approx_tokens": tblib.estimate(text)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_playbook(args):
    doc = htmldoc.from_string(_read(args.input))
    queries = list(args.query or [])
    if args.query_file:
        queries += [ln.strip() for ln in _read(args.query_file).splitlines() if ln.strip()]
    pb = playbooklib.generate(
        doc, brand=args.brand, category=args.category,
        engines=args.engine or None, roots=args.root or None,
        content_type=args.content_type, queries=queries or None, market=args.market,
        robots_text=_read(args.robots) if args.robots else None,
        llms_text=_read(args.llms) if args.llms else None,
        competitors=args.competitor or None)
    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(playbooklib.render_html(pb))
        print("写入 HTML 作战手册 %s" % args.html)
    if args.json:
        print(json.dumps(pb, ensure_ascii=False, indent=2))
        return 0
    if not args.html or args.out:
        _emit(playbooklib.render_markdown(pb), args.out)
    return 0


def cmd_compare(args):
    queries = list(args.query or [])
    if args.query_file:
        queries += [ln.strip() for ln in _read(args.query_file).splitlines() if ln.strip()]
    if not os.path.exists(args.input):
        print("找不到文件: %s" % args.input, file=sys.stderr)
        return 2
    pages = [(args.label or "你", htmldoc.from_string(_read(args.input)))]
    for i, spec in enumerate(args.competitor_page or [], 1):
        if "::" in spec:
            lbl, path = spec.split("::", 1)
        else:
            lbl, path = "竞品%d" % i, spec
        path = path.strip()
        if not os.path.exists(path):
            print("找不到竞品文件: %s(来自 --competitor-page %s)" % (path, spec), file=sys.stderr)
            return 2
        pages.append((lbl.strip(), htmldoc.from_string(_read(path))))
    result = playbooklib.compare(pages, brand=args.brand, queries=queries or None,
                                 market=args.market)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    _emit(playbooklib.render_compare(result), args.out)
    return 0


def cmd_measure(args):
    if args.kit:
        rows = promptlib.generate(args.brand or "品牌", args.category or "品类", limit=20) \
            if (args.brand and args.category) else []
        kit = measurelib.collection_kit(args.brand, args.engine or [], rows,
                                        competitors=args.competitor or None)
        if args.json:
            print(json.dumps(kit, ensure_ascii=False, indent=2))
        else:
            _emit(measurelib.render_kit(kit), args.out)
        return 0
    if not args.input:
        print("measure 非 --kit 模式需要 --input records.json(或加 --kit 出采集工具包)", file=sys.stderr)
        return 2
    records = json.loads(_read(args.input))
    if isinstance(records, dict):
        records = records.get("records", [])
    facts = json.loads(_read(args.facts)) if args.facts else None
    aliases = json.loads(_read(args.aliases)) if args.aliases else None
    m = measurelib.measure_all(records, args.brand, competitors=args.competitor or None,
                               facts=facts, aliases=aliases, brand_domain=args.brand_domain)
    if args.json:
        print(json.dumps(m, ensure_ascii=False, indent=2))
    else:
        _emit(measurelib.render_measure(m), args.out)
    return 0


def cmd_sourcing(args):
    p = sourcinglib.plan(
        category=args.category, roots=args.root or None,
        engines=args.engine or None, content_type=args.content_type,
        market=args.market)
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    _emit(sourcinglib.render_markdown(p), args.out)
    return 0


def cmd_cescore(args):
    doc = htmldoc.from_string(_read(args.input))
    queries = list(args.query or [])
    if args.query_file:
        queries += [ln.strip() for ln in _read(args.query_file).splitlines() if ln.strip()]
    queries = queries or None
    if args.annotate:
        ann = celib.annotate(doc, queries=queries)
        if args.json:
            print(json.dumps(ann, ensure_ascii=False, indent=2))
        else:
            _emit(celib.render_annotation(ann), args.out)
        return 0
    result = celib.score(doc, market=args.market, queries=queries)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["score"] >= args.fail_under else 1
    _emit(celib.render(result), args.out)
    return 0 if result["score"] >= args.fail_under else 1


def cmd_baidu_index_check(args):
    site = args.site
    text = (
        "# 百度/国产搜索收录状态自查(工具不联网,给查法)\n"
        "# 1) 收录量粗查:在百度搜索框输入(整页是否被收录):\n"
        "site:%s\n"
        "# 2) 单页是否收录:\n"
        "site:%s inurl:你的路径\n"
        "# 3) 权威看后台:百度搜索资源平台 > 数据监控 > 索引量 / 抓取诊断 / 抓取频次\n"
        "# 4) 神马/搜狗同理用各自 site: 语法;收录是国产 AI 可见的前置(求收录占平台)。\n"
        % (site, site))
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
                    choices=["article", "faqpage", "howto", "product",
                             "organization", "person", "website",
                             "breadcrumb", "itemlist", "review",
                             "action", "speakable", "software"])
    sc.add_argument("--title")
    sc.add_argument("--name")
    sc.add_argument("--description")
    sc.add_argument("--author")
    sc.add_argument("--author-url")
    sc.add_argument("--same-as", action="append")
    sc.add_argument("--org")
    sc.add_argument("--url")
    sc.add_argument("--logo", help="organization: logo URL")
    sc.add_argument("--founder", help="organization: 创始人")
    sc.add_argument("--job-title", help="person: 职位")
    sc.add_argument("--knows-about", action="append", help="person: 专长,可多次")
    sc.add_argument("--item", action="append", help='breadcrumb/itemlist: "名称::url",可多次')
    sc.add_argument("--action", choices=["order", "reserve", "search", "subscribe", "register"],
                    help="action: 动作类型")
    sc.add_argument("--selector", action="append", help="speakable: CSS 选择器,可多次")
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

    # rewrite
    rw = sub.add_parser("rewrite", help="改写指令编译器(吃打分→出改写指令包)")
    rw.add_argument("--input", required=True, help="HTML 文件")
    rw.add_argument("--engine", help="目标引擎(perplexity/claude/gemini/chatgpt/豆包/元宝/文心/deepseek)")
    rw.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    rw.add_argument("--lang", choices=["zh", "en"], default="zh")
    rw.add_argument("--json", action="store_true")
    rw.add_argument("--out")
    rw.set_defaults(func=cmd_rewrite)

    # brief
    br = sub.add_parser("brief", help="GEO Content Brief 生成器")
    br.add_argument("--topic", required=True)
    br.add_argument("--question", help="主问句")
    br.add_argument("--section", action="append", help="H2 小标题(问句形态),可多次")
    br.add_argument("--entity", action="append", help="必须覆盖的实体,可多次")
    br.add_argument("--paa", action="append", help="必答问句,可多次")
    br.add_argument("--engine", help="目标引擎")
    br.add_argument("--lang", choices=["zh", "en"], default="zh")
    br.add_argument("--intent", help="目标查询(自动分类搜索意图,指导内容骨架)")
    br.add_argument("--json", action="store_true")
    br.add_argument("--out")
    br.set_defaults(func=cmd_brief)

    # prompts
    pr = sub.add_parser("prompts", help="buyer prompt 集生成器")
    pr.add_argument("--brand", required=True)
    pr.add_argument("--category", required=True)
    pr.add_argument("--competitor", action="append")
    pr.add_argument("--problem", action="append")
    pr.add_argument("--persona", action="append")
    pr.add_argument("--geo", action="append")
    pr.add_argument("--usecase", action="append")
    pr.add_argument("--lang", choices=["zh", "en"], default="zh")
    pr.add_argument("--limit", type=int)
    pr.add_argument("--csv", action="store_true")
    pr.add_argument("--out")
    pr.set_defaults(func=cmd_prompts)

    # sov
    sv = sub.add_parser("sov", help="Share of Voice 度量")
    sv.add_argument("--input", required=True, help="records JSON(prompt/engine/answer)")
    sv.add_argument("--brand", required=True)
    sv.add_argument("--competitor", action="append")
    sv.add_argument("--aliases", help="别名 JSON {canonical:[alias..]}")
    sv.add_argument("--brand-domain")
    sv.add_argument("--competitor-domains", help="JSON {brand:domain}")
    sv.set_defaults(func=cmd_sov)

    # diagnose
    dg = sub.add_parser("diagnose", help="「为何没被引用」7 根因诊断")
    dg.add_argument("--input", required=True, help="HTML 文件")
    dg.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    dg.add_argument("--json", action="store_true")
    dg.set_defaults(func=cmd_diagnose)

    # agentready
    ar = sub.add_parser("agentready", help="WebMCP / agent 任务就绪审计")
    ar.add_argument("--input", required=True, help="HTML 文件")
    ar.add_argument("--json", action="store_true")
    ar.set_defaults(func=cmd_agentready)

    # batch
    ba = sub.add_parser("batch", help="批量站点审计")
    ba.add_argument("inputs", nargs="+", help="多个 HTML 文件")
    ba.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    ba.add_argument("--html", help="输出 HTML 报告路径")
    ba.add_argument("--fail-under", type=int, default=0)
    ba.set_defaults(func=cmd_batch)

    # report
    rp = sub.add_parser("report", help="评分渲染成 HTML / SARIF")
    rp.add_argument("--input", required=True)
    rp.add_argument("--format", choices=["html", "sarif"], default="html")
    rp.add_argument("--robots")
    rp.add_argument("--llms")
    rp.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    rp.add_argument("--out")
    rp.set_defaults(func=cmd_report)

    # files
    fl = sub.add_parser("files", help="生成 AI 发现/答案文件组")
    fl.add_argument("--out-dir", required=True)
    fl.add_argument("--site")
    fl.add_argument("--url")
    fl.add_argument("--author")
    fl.add_argument("--date")
    fl.add_argument("--allow-train", action="store_true", help="放行训练类 bot")
    fl.set_defaults(func=cmd_files)

    # attribution
    at = sub.add_parser("attribution", help="GEO 归因物料 / 日志解析")
    at.add_argument("--url", help="站点 URL(出 UTM 示例)")
    at.add_argument("--log", help="access log 文件(解析 AI 爬虫 UA)")
    at.add_argument("--out")
    at.set_defaults(func=cmd_attribution)

    # recommend
    re_ = sub.add_parser("recommend", help="平台发布推荐(给目标引擎→推荐发哪)")
    re_.add_argument("--engine", action="append",
                     help="目标引擎(豆包/元宝/deepseek/kimi/文心/通义/chatgpt/perplexity/gemini/claude 或 cn-all/overseas-all),可多次")
    re_.add_argument("--content-type", choices=["video", "tech", "种草", "消费", "b2b", "b2c"],
                     help="内容类型(追加适配平台)")
    re_.add_argument("--reverse", help="反向查:某平台能喂哪些 AI")
    re_.add_argument("--top", type=int, help="只看前 N 个")
    re_.add_argument("--json", action="store_true")
    re_.add_argument("--out")
    re_.set_defaults(func=cmd_recommend)

    # intent
    it = sub.add_parser("intent", help="搜索意图分类(信息/商业/交易/导航)")
    it.add_argument("--query", required=True, help="查询或标题")
    it.add_argument("--json", action="store_true")
    it.add_argument("--out")
    it.set_defaults(func=cmd_intent)

    # baidu-push
    bp = sub.add_parser("baidu-push", help="百度主动推送脚本(国内收录第一杠杆)")
    bp.add_argument("--site", required=True, help="ICP 备案主域")
    bp.add_argument("--token", help="百度搜索资源平台 token")
    bp.add_argument("--url", action="append", help="要提交的 URL,可多次")
    bp.add_argument("--url-file", help="每行一个 URL 的文件")
    bp.add_argument("--fast", action="store_true", help="快速收录(需权益)")
    bp.add_argument("--out")
    bp.set_defaults(func=cmd_baidu_push)

    # hreflang
    hf = sub.add_parser("hreflang", help="多语言 hreflang 标注")
    hf.add_argument("--locale", action="append", help='"zh-CN::url",可多次')
    hf.add_argument("--x-default", help="x-default 兜底 URL")
    hf.add_argument("--out")
    hf.set_defaults(func=cmd_hreflang)

    # factcheck
    fc = sub.add_parser("factcheck", help="品牌错误信息纠正(吃 AI 回答 + 品牌真相)")
    fc.add_argument("--input", required=True, help="records JSON")
    fc.add_argument("--brand", required=True)
    fc.add_argument("--facts", required=True, help="facts JSON: [{attribute,truth,wrong:[]}]")
    fc.add_argument("--aliases")
    fc.add_argument("--json", action="store_true")
    fc.set_defaults(func=cmd_factcheck)

    # lostprompt
    lp = sub.add_parser("lostprompt", help="竞品替换分析(找输的 prompt)")
    lp.add_argument("--input", required=True, help="records JSON")
    lp.add_argument("--brand", required=True)
    lp.add_argument("--competitor", action="append")
    lp.add_argument("--aliases")
    lp.add_argument("--json", action="store_true")
    lp.add_argument("--out")
    lp.set_defaults(func=cmd_lostprompt)

    # cannibalize
    cn = sub.add_parser("cannibalize", help="关键词蚕食检测(多页)")
    cn.add_argument("inputs", nargs="+", help="多个 HTML 文件")
    cn.add_argument("--threshold", type=float, default=0.5, help="关键词重叠阈值")
    cn.set_defaults(func=cmd_cannibalize)

    # internal-links
    il = sub.add_parser("internal-links", help="内链/孤儿页审计(多页)")
    il.add_argument("inputs", nargs="+", help="多个 HTML 文件")
    il.add_argument("--host", action="append", help="站点域名(判带域名的链接为站内)")
    il.add_argument("--home", default="/", help="首页 path(不算孤儿)")
    il.set_defaults(func=cmd_internallinks)

    # cwv
    cv = sub.add_parser("cwv", help="Core Web Vitals 评估(喂 PSI 数值)")
    cv.add_argument("--lcp", type=float, help="LCP 秒")
    cv.add_argument("--inp", type=float, help="INP 毫秒")
    cv.add_argument("--cls", type=float, help="CLS 数值")
    cv.add_argument("--psi", help="PageSpeed JSON 文件({lcp,inp,cls})")
    cv.set_defaults(func=cmd_cwv)

    # token
    tk = sub.add_parser("token", help="token 预算估算(近似)")
    tk.add_argument("--input", help="文本文件")
    tk.add_argument("--text", help="直接传文本")
    tk.add_argument("--budget", type=int, help="token 预算上限")
    tk.set_defaults(func=cmd_token)

    # playbook
    pb = sub.add_parser("playbook", help="★旗舰:一键出完整 GEO 作战手册(八层瓶颈定位+诊断+信源+改写+监测)")
    pb.add_argument("--input", required=True, help="HTML 文件")
    pb.add_argument("--brand", help="品牌名")
    pb.add_argument("--category", help="品类/业务")
    pb.add_argument("--engine", action="append", help="目标引擎,可多次")
    pb.add_argument("--root", action="append", help="词根,可多次")
    pb.add_argument("--content-type", choices=["video", "tech", "种草", "消费", "b2b", "b2c"])
    pb.add_argument("--query", action="append", help="目标问句,可多次")
    pb.add_argument("--query-file", help="每行一个目标问句")
    pb.add_argument("--competitor", action="append", help="竞品,可多次")
    pb.add_argument("--robots", help="robots.txt 文件")
    pb.add_argument("--llms", help="llms.txt 文件")
    pb.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    pb.add_argument("--html", help="输出静态可打印 HTML 作战手册到此路径")
    pb.add_argument("--json", action="store_true")
    pb.add_argument("--out", help="输出 markdown 到此路径")
    pb.set_defaults(func=cmd_playbook)

    # compare
    cp = sub.add_parser("compare", help="对标作战(你的页 vs 竞品页,逐维逐要素比强弱+差距点)")
    cp.add_argument("--input", required=True, help="你的 HTML 文件")
    cp.add_argument("--label", help="你的标签(默认'你')")
    cp.add_argument("--competitor-page", action="append", help='竞品 HTML:"标签::路径" 或 路径,可多次')
    cp.add_argument("--brand")
    cp.add_argument("--query", action="append", help="目标问句,可多次")
    cp.add_argument("--query-file")
    cp.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    cp.add_argument("--json", action="store_true")
    cp.add_argument("--out")
    cp.set_defaults(func=cmd_compare)

    # measure
    me = sub.add_parser("measure", help="监测采集闭环(--kit 出采集工具包;喂 records 一键 sov+lostprompt+factcheck)")
    me.add_argument("--kit", action="store_true", help="出采集工具包(协议+prompt集+records模板)")
    me.add_argument("--input", help="records JSON(measure 模式)")
    me.add_argument("--brand", help="品牌名")
    me.add_argument("--category", help="品类(--kit 时生成 prompt 集用)")
    me.add_argument("--engine", action="append", help="目标引擎,可多次")
    me.add_argument("--competitor", action="append", help="竞品,可多次")
    me.add_argument("--facts", help="facts JSON(factcheck 用)")
    me.add_argument("--aliases", help="别名 JSON")
    me.add_argument("--brand-domain")
    me.add_argument("--json", action="store_true")
    me.add_argument("--out")
    me.set_defaults(func=cmd_measure)

    # sourcing
    so = sub.add_parser("sourcing", help="信源策略规划(八层2-4:词根→问句矩阵+信源偏好诊断+投放SOP+诊断闭环)")
    so.add_argument("--category", help="品类/业务")
    so.add_argument("--root", action="append", help="词根,可多次")
    so.add_argument("--engine", action="append",
                    help="目标引擎(豆包/元宝/deepseek/.../cn-all/overseas-all),可多次")
    so.add_argument("--content-type", choices=["video", "tech", "种草", "消费", "b2b", "b2c"])
    so.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    so.add_argument("--json", action="store_true")
    so.add_argument("--out")
    so.set_defaults(func=cmd_sourcing)

    # cescore
    ce = sub.add_parser("cescore", help="内容工程 11 要素加权评分(被引用拆解,WaytoAGI 方法论)")
    ce.add_argument("--input", required=True, help="HTML 文件")
    ce.add_argument("--market", choices=["auto", "cn", "global"], default="auto")
    ce.add_argument("--query", action="append", help="目标问句(真需求匹配,可多次)")
    ce.add_argument("--query-file", help="每行一个目标问句的文件")
    ce.add_argument("--annotate", action="store_true", help="段落级要素标注(逐段改写指引)")
    ce.add_argument("--json", action="store_true")
    ce.add_argument("--fail-under", type=int, default=0)
    ce.add_argument("--out")
    ce.set_defaults(func=cmd_cescore)

    # baidu-index-check
    bic = sub.add_parser("baidu-index-check", help="百度/国产搜索收录状态自查指引")
    bic.add_argument("--site", required=True)
    bic.add_argument("--out")
    bic.set_defaults(func=cmd_baidu_index_check)

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
