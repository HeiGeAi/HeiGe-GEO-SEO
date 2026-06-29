"""GEO 作战手册编排器:把整套工具收口成一个交付物。

产品的正门。一条命令吃 网页 + 品牌 + 品类 + 目标引擎,产出一份完整 GEO 作战手册:
  1. 八层瓶颈定位(产品的脑子):综合 score + cescore + diagnose,判定卡在八层哪一层、先打哪条腿
  2. 现状诊断:6 维评分 + 内容工程 11 要素 + 为何没被引用根因
  3. 信源策略:词根→问句矩阵 + 引擎信源偏好 + 分层投放(sourcing)
  4. 内容改写指引:逐段要素标注 + 改写指令(证据引用层优先)
  5. 监测采集闭环:buyer prompt 集 + 采集协议 + 喂回 sov/lostprompt/factcheck
  6. 统一行动清单:跨层按杠杆位排序(方法论先验,非逐项 ROI 测算)

编排已有 lib,不重造轮子。纯标准库,确定性。
"""

import html as _html

from . import scoring
from . import content_engineering as ce
from . import diagnose as diaglib
from . import sourcing as sourcinglib
from . import instruction as instrlib
from . import prompts as promptlib
from . import measure as measurelib


# 收录/索引层风险信号:当前 diagnose 在国内市场只产出 ICP/备案 一条信号,
# 故只认这两个词,别假装覆盖了完整收录诊断(robots/真实收录要 baidu-index-check 实测)。
_INDEX_RISK = ("备案", "ICP")
# 内容质量瓶颈的经验阈值(非方法论硬线,可按自家实测调)
_CONTENT_WEAK_BELOW = 55      # cescore 总分(0-100)低于此,内容是瓶颈
_EXTRACT_WEAK_BELOW = 0.5     # 可抽取性(D 维)得分率低于此,内容是瓶颈
_BORDER_BAND = 10             # 内容分落在阈值 ±此范围且语义低置信时,判断标"倾向"


def _dim_ratio(sc, dim_key):
    """某维度得分率(earned/weight),拿不到返回 None。"""
    for d in sc["dimensions"]:
        if d["key"] == dim_key:
            w = d.get("weight_evaluated") or d.get("weight") or 0
            return (d["earned"] / w) if w else None
    return None


def _locate_bottleneck(sc, ce_res, diag, market):
    """八层瓶颈定位:判定卡在哪一层、先打哪条腿。产品的脑子。"""
    content_score = ce_res["score"]              # 内容质量层(5-7)总分
    extract_ratio = _dim_ratio(sc, "D")          # 可抽取性得分率
    evidence = ce_res["evidence_layer_raw"]      # 证据引用层原始加权上限 43(归一化后约占 44%)
    index_risks = [f for f in diag["findings"]
                   if f["status"] in ("fail", "warn")
                   and any(k in f["cause"] for k in _INDEX_RISK)]
    # 语义要素无 query 时低置信,内容分会有约 8 分摆动;落在阈值边界带时判断只标"倾向"
    sem_low_conf = any(e["key"] == "semantic" and e["low_confidence"]
                       for e in ce_res["elements"])
    near_border = abs(content_score - _CONTENT_WEAK_BELOW) <= _BORDER_BAND
    confidence = "低(语义未传 --query 且内容分接近阈值,建议传目标问句复算再定打哪条腿)" \
        if (sem_low_conf and near_border) else "高"

    # 判定优先级:内容太弱先修内容;内容过关但国内收录有障碍修索引;否则信源策略
    if content_score < _CONTENT_WEAK_BELOW or (extract_ratio is not None and extract_ratio < _EXTRACT_WEAK_BELOW):
        layer = "内容质量层(5-7 重排/装配/引用)"
        first = ("先补内容:证据引用层原始加权 %s/43,用 cescore --annotate 逐段补 "
                 "权威原文引语 + 真实统计数据 + 带出处可引用性。内容抽不动,发到哪都引不了。"
                 % evidence)
    elif market == "cn" and index_risks:
        layer = "索引层(2 收录·当前仅检测 ICP 备案信号)"
        first = ("先解决收录:%s。国内是求收录加占平台,没被收录 AI 检索池里就没有你。"
                 "备案只是收录前置之一,是否真被收录须跑 baidu-index-check 实测,"
                 "再 baidu-push 主动推送 + 铺高权重生态平台。"
                 % "、".join(r["cause"] for r in index_risks[:2]))
    else:
        layer = "信源策略层(3-4 查询/检索)"
        first = ("内容质量过关,瓶颈在信源:跑 sourcing 出该引擎的信源偏好与分层投放,"
                 "先发 P0 命脉平台试投,再跑监测闭环看是否被引。")
    return {
        "bottleneck_layer": layer,
        "confidence": confidence,
        "content_score": content_score,
        "evidence_layer": evidence,
        "extract_ratio": round(extract_ratio, 2) if extract_ratio is not None else None,
        "index_risks": [r["cause"] for r in index_risks],
        "first_action": first,
        "detection_boundary": "索引层只检测 ICP 备案信号,真实收录须 baidu-index-check 实测;"
                              "阈值 55/0.5 为经验值非方法论硬线。",
    }


def _unified_actions(sc, ce_res, diag, src):
    """跨层统一行动清单,按杠杆位排序(证据引用层 > 收录 > schema/结构 > 信源投放 > 监测)。

    这是方法论先验的优先级分层,不是逐项 ROI(收益/成本)测算。证据引用层 43% 是被引用
    第一杠杆、国内收录是前置、监测收口,故定此序;同 prio 内沿用 cescore 已排好的加权欠分序。
    """
    actions = []
    # 1. 内容工程最该先补(证据引用层优先,cescore 已排好序)
    for w in ce_res["weakest"]:
        prio = 1 if w["layer"] == "证据引用层" else 3
        actions.append({"prio": prio, "layer": "内容质量", "action": "补「%s」:%s" % (w["element"], w["formula"])})
    # 2. 收录/索引障碍(国内第一前置)
    for f in diag["findings"]:
        if f["status"] in ("fail", "warn") and any(k in f["cause"] for k in _INDEX_RISK):
            actions.append({"prio": 2, "layer": "索引收录", "action": "%s → %s" % (f["cause"], f.get("fix") or "核实")})
    # 3. 6 维评分最弱项(schema/结构/信任)
    for w in sc["weakest"][:3]:
        actions.append({"prio": 4, "layer": "基础设施", "action": "%s/%s %s:%s" % (w["dim"], w["id"], w["name"], w["note"])})
    # 4. 信源投放(P0 首发)
    p0 = src["delivery_sop"]["tiers"]["P0"]
    if p0:
        plats = "、".join(it["platform"] for it in p0)
        actions.append({"prio": 5, "layer": "信源投放", "action": "P0 首发命脉平台:%s" % plats})
    # 5. 监测
    actions.append({"prio": 6, "layer": "监测闭环",
                    "action": "跑 buyer prompt 集去目标引擎采样(每问句每平台 5 次),喂回 sov/lostprompt 看占位"})
    actions.sort(key=lambda a: a["prio"])
    return actions


def generate(doc, brand, category, engines=None, roots=None, content_type=None,
             queries=None, market="auto", robots_text=None, llms_text=None,
             competitors=None):
    """生成完整 GEO 作战手册。"""
    sc = scoring.score_document(doc, robots_text=robots_text, llms_text=llms_text, market=market)
    eff_market = sc["market"]
    ce_res = ce.score(doc, market=eff_market, queries=queries)
    ann = ce.annotate(doc, queries=queries)
    diag = diaglib.diagnose(doc, market=eff_market)
    roots = roots or ([category] if category else [])
    src = sourcinglib.plan(category, roots, engines, content_type=content_type, market=market)
    instr = instrlib.compile_instructions(sc, target_engine=(engines[0] if engines else None))
    prompt_rows = promptlib.generate(brand, category, competitors=competitors,
                                      limit=20) if (brand and category) else []
    bottleneck = _locate_bottleneck(sc, ce_res, diag, eff_market)
    actions = _unified_actions(sc, ce_res, diag, src)
    kit = measurelib.collection_kit(brand, engines or [], prompt_rows, competitors=competitors)

    return {
        "brand": brand, "category": category, "market": eff_market,
        "target_engines": src["target_engines"],
        "bottleneck": bottleneck,
        "score_6dim": {"total": sc["score"], "grade": sc["grade"],
                       "geo": sc["geo_score"], "seo": sc["seo_score"],
                       "weakest": sc["weakest"][:3]},
        "content_engineering": {"score": ce_res["score"], "grade": ce_res["grade"],
                                "evidence_layer_raw": ce_res["evidence_layer_raw"],
                                "query_coverage": ce_res.get("query_coverage"),
                                "weakest": ce_res["weakest"]},
        "annotate_paragraphs": ann["paragraphs"],
        "diagnosis": {"verdict": diag["verdict"], "failed_count": diag["failed_count"],
                      "findings": diag["findings"]},
        "sourcing": src,
        "rewrite_instructions": instr,
        "measure_kit": kit,
        "unified_actions": actions,
        "note": "本手册离线生成,确定性可复现。监测环需宿主 agent 或人工去目标引擎采集 AI 回答,"
                "喂回 sov/lostprompt/factcheck 才闭合。所有引语/统计/引用只用真实素材,绝不编造。",
    }


def render_markdown(pb):
    o = ["# GEO 作战手册:%s" % (pb["brand"] or pb["category"] or "目标站点"), ""]
    o.append("> 市场: %s | 目标引擎: %s | 本手册离线确定性生成,工具开源 MIT" % (
        pb["market"], "、".join(pb["target_engines"]) or "(未指定)"))
    o.append("")

    b = pb["bottleneck"]
    o.append("## 一、八层瓶颈定位(先看这里)")
    o.append("**瓶颈层:%s**(判断置信度:%s)" % (b["bottleneck_layer"], b.get("confidence", "高")))
    o.append("")
    o.append("**第一动作:%s**" % b["first_action"])
    o.append("")
    o.append("- 内容工程总分 %s/100,证据引用层 %s/43%s" % (
        b["content_score"], b["evidence_layer"],
        (",可抽取性得分率 %s" % b["extract_ratio"]) if b["extract_ratio"] is not None else ""))
    if b["index_risks"]:
        o.append("- 收录/索引风险:%s" % "、".join(b["index_risks"]))
    o.append("")

    o.append("## 二、统一行动清单(按杠杆位排序:证据层>收录>结构>投放>监测,方法论先验非逐项 ROI 测算)")
    for i, a in enumerate(pb["unified_actions"], 1):
        o.append("%d. [%s] %s" % (i, a["layer"], a["action"]))
    o.append("")

    s = pb["score_6dim"]
    o.append("## 三、现状诊断")
    o.append("- 6 维评分:**%s/100**(%s) | GEO %s | SEO %s" % (
        s["total"], s["grade"], s["geo"], s["seo"]))
    ce_ = pb["content_engineering"]
    qc = (",需求覆盖率 %s" % ce_["query_coverage"]) if ce_["query_coverage"] is not None else ""
    o.append("- 内容工程 11 要素:**%s/100**(%s),证据引用层 %s/43%s" % (
        ce_["score"], ce_["grade"], ce_["evidence_layer_raw"], qc))
    o.append("- 为何没被引用:%s(%d 项障碍)" % (pb["diagnosis"]["verdict"], pb["diagnosis"]["failed_count"]))
    o.append("")

    o.append("## 四、信源策略(发哪、被谁抓)")
    o.append(sourcinglib.render_markdown(pb["sourcing"]).split("\n", 2)[-1])
    o.append("")

    o.append("## 五、监测采集闭环")
    o.append(measurelib.render_kit(pb["measure_kit"]))
    o.append("")
    o.append("> " + pb["note"])
    return "\n".join(o)


def compare(pages, brand=None, queries=None, market="auto"):
    """对标作战:你的页 vs 竞品页,逐维逐要素比强弱。

    pages:[(label, doc), ...],第一个是你,其余是竞品。每页打 6 维 + 内容工程 11 要素,
    输出排名 + 你落后的要素(差距点)+ 一句话裁决。
    """
    rows = []
    for label, doc in pages:
        sc = scoring.score_document(doc, market=market)
        ce_res = ce.score(doc, market=sc["market"], queries=queries)
        rows.append({
            "label": label,
            "score_6dim": sc["score"],
            "content_score": ce_res["score"],
            "evidence_layer_raw": ce_res["evidence_layer_raw"],
            "elements": {x["key"]: x["score_0_1"] for x in ce_res["elements"]},
            "element_meta": {x["key"]: x["element"] for x in ce_res["elements"]},
        })
    if not rows:
        return {"rows": [], "you": None, "gaps": [], "verdict": "无对比对象"}
    you = rows[0]
    competitors = rows[1:]
    # 内容质量综合分(6维与内容工程等权平均;两者在结构/证据/权威上有重叠,仅作离线相对排名)
    for r in rows:
        r["combined"] = round((r["score_6dim"] + r["content_score"]) / 2, 1)
    ranked = sorted(rows, key=lambda r: -r["combined"])
    you_rank = ranked.index(you) + 1
    # 你落后的要素:只跟综合分不低于你的竞品比,别拿垃圾页在 fluency/readability 上的虚高单要素当差距
    strong_comps = [c for c in competitors if c["combined"] >= you["combined"]]
    gaps = []
    for key, name in you["element_meta"].items():
        comp_max = max((c["elements"].get(key, 0) for c in strong_comps), default=0)
        if comp_max > you["elements"].get(key, 0) + 0.05:
            gaps.append({"element": name, "your": round(you["elements"].get(key, 0), 2),
                         "best_competitor": round(comp_max, 2),
                         "gap": round(comp_max - you["elements"].get(key, 0), 2)})
    gaps.sort(key=lambda g: -g["gap"])
    second = max((c["combined"] for c in competitors), default=None)
    if not competitors:
        verdict = "只给了你自己,没有竞品可比。"
    elif second is not None and you["combined"] <= second and you_rank == 1:
        verdict = "你和头名打平(内容质量综合分均 %s),还没拉开差距,盯防 %d 个被追平要素(仅内容质量层离线估算)。" % (
            you["combined"], len(gaps))
    elif you_rank == 1:
        verdict = "你内容质量综合分领先(%s),守住,盯防 %d 个被追平要素(仅内容质量层离线估算,实际是否被引用须跑 measure)。" % (
            you["combined"], len(gaps))
    else:
        verdict = "你排第 %d/%d,内容质量综合分 %s 落后头名 %s。先补差距最大的证据/结构要素(仅内容质量层离线估算)。" % (
            you_rank, len(rows), you["combined"], ranked[0]["combined"])
    return {
        "rows": [{"label": r["label"], "rank": ranked.index(r) + 1,
                  "score_6dim": r["score_6dim"], "content_score": r["content_score"],
                  "evidence_layer_raw": r["evidence_layer_raw"], "combined": r["combined"]}
                 for r in rows],
        "you": you["label"], "you_rank": you_rank,
        "gaps": gaps[:8],
        "verdict": verdict,
        "note": "对标只比内容质量层(可离线);内容质量综合分=6维与内容工程等权平均,两者在结构/证据上有重叠,"
                "仅作相对排名不是权威总评。差距要素只跟综合分不低于你的竞品比,只用真实素材补,绝不编造。"
                "谁真被引用还要跑 measure 采样。",
    }


def render_compare(c):
    o = ["# 对标作战:内容质量层", ""]
    o.append("**裁决:%s**" % c["verdict"])
    o.append("")
    o.append("| 排名 | 对象 | 内容质量综合分 | 6 维 | 内容工程 | 证据层/43 |")
    o.append("|---|---|---|---|---|---|")
    for r in sorted(c["rows"], key=lambda r: r["rank"]):
        mark = " ★你" if r["label"] == c["you"] else ""
        o.append("| %d | %s%s | %s | %s | %s | %s |" % (
            r["rank"], r["label"], mark, r["combined"], r["score_6dim"],
            r["content_score"], r["evidence_layer_raw"]))
    o.append("")
    if c["gaps"]:
        o.append("## 你落后的要素(差距最大优先,补真实素材)")
        for g in c["gaps"]:
            o.append("- %s:你 %s vs 竞品最佳 %s(差 %s)" % (
                g["element"], g["your"], g["best_competitor"], g["gap"]))
    else:
        o.append("各要素你都不落后,守住即可。")
    o.append("")
    o.append("> " + c["note"])
    return "\n".join(o)


# 瓶颈层 → 主题色
_LAYER_COLOR = [("内容质量", "#e8833a"), ("索引", "#d73027"), ("信源", "#2b6cb0")]
# 行动层 → 标签色
_ACTION_COLOR = {"内容质量": "#e8833a", "索引收录": "#d73027", "基础设施": "#7c5cbf",
                 "信源投放": "#2b6cb0", "监测闭环": "#1a9850"}


def _layer_color(layer_str):
    for k, c in _LAYER_COLOR:
        if k in layer_str:
            return c
    return "#444"


def _bar(pct, color, label):
    pct = max(0.0, min(100.0, pct))
    return ('<div class="barwrap"><div class="barlabel">%s</div>'
            '<div class="bar"><div class="fill" style="width:%.1f%%;background:%s"></div></div></div>'
            % (label, pct, color))


def render_html(pb):
    e = _html.escape
    b = pb["bottleneck"]
    s = pb["score_6dim"]
    ce_ = pb["content_engineering"]
    color = _layer_color(b["bottleneck_layer"])
    conf = b.get("confidence", "高")

    actions = []
    for i, a in enumerate(pb["unified_actions"], 1):
        c = _ACTION_COLOR.get(a["layer"], "#444")
        actions.append('<li><span class="tag" style="background:%s">%s</span> %s</li>'
                       % (c, e(a["layer"]), e(a["action"])))

    tiers_html = []
    for tier in ["P0", "P1", "P2"]:
        items = pb["sourcing"]["delivery_sop"]["tiers"][tier]
        if not items:
            continue
        chips = "".join('<span class="chip">%s<small>·%d</small></span>'
                        % (e(it["platform"]), it["score"]) for it in items)
        label = {"P0": "跨引擎共识/命脉首发", "P1": "单引擎高权重/次轮", "P2": "补充覆盖,按品类回判"}[tier]
        tiers_html.append('<div class="tier"><div class="tierhd"><b>%s</b> %s</div>%s</div>'
                          % (tier, e(label), chips))

    prompts = pb["measure_kit"].get("prompts_to_ask", [])[:12]
    prompt_lis = "".join("<li>%s</li>" % e(p) for p in prompts)

    title = e(pb["brand"] or pb["category"] or "目标站点")
    evid = ce_["evidence_layer_raw"]
    qc = ce_.get("query_coverage")
    qc_html = (' · 需求覆盖率 <b>%s</b>' % qc) if qc is not None else ""

    return """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEO 作战手册 · %(title)s</title><style>
*{box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;
max-width:880px;margin:0 auto;padding:28px 20px;color:#222;background:#fafafa;line-height:1.6}
h1{font-size:26px;margin:0 0 4px}
.meta{color:#666;font-size:13px;margin-bottom:20px}
.hero{border-left:6px solid %(color)s;background:#fff;border-radius:8px;padding:18px 20px;
box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:20px}
.hero .lab{font-size:12px;color:#888;letter-spacing:1px}
.hero .layer{font-size:22px;font-weight:700;color:%(color)s;margin:2px 0 6px}
.hero .conf{font-size:12px;color:#888}
.hero .act{margin-top:10px;padding-top:10px;border-top:1px solid #f0f0f0;font-size:15px}
.card{background:#fff;border-radius:8px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px}
.card h2{font-size:16px;margin:0 0 12px;color:#333}
.barwrap{margin:8px 0}
.barlabel{font-size:13px;color:#555;margin-bottom:3px}
.bar{height:14px;background:#eee;border-radius:7px;overflow:hidden}
.fill{height:100%%;border-radius:7px}
ol.actions{margin:0;padding-left:22px}
ol.actions li{margin:7px 0;font-size:14px}
.tag{color:#fff;font-size:11px;padding:1px 7px;border-radius:4px;margin-right:6px;white-space:nowrap}
.tier{margin:10px 0}
.tierhd{font-size:13px;color:#555;margin-bottom:5px}
.chip{display:inline-block;background:#eef3fb;color:#2b6cb0;border-radius:14px;padding:3px 11px;
margin:3px 5px 3px 0;font-size:13px}
.chip small{color:#88a}
ul.prompts{columns:2;font-size:13px;color:#555;margin:6px 0}
.note{font-size:12px;color:#888;border-top:1px solid #eee;padding-top:12px;margin-top:8px}
@media print{body{background:#fff}.card,.hero{box-shadow:none;border:1px solid #eee}ul.prompts{columns:1}}
</style></head><body>
<h1>GEO 作战手册 · %(title)s</h1>
<div class="meta">市场 %(market)s · 目标引擎 %(engines)s · 离线确定性生成 · HeiGe-GEO-SEO 开源 MIT</div>

<div class="hero">
<div class="lab">八层瓶颈定位 · 先看这里</div>
<div class="layer">%(layer)s</div>
<div class="conf">判断置信度:%(conf)s</div>
<div class="act"><b>第一动作:</b>%(first)s</div>
</div>

<div class="card"><h2>评分</h2>
%(bar6)s
%(barce)s
%(barev)s
<div style="font-size:12px;color:#888;margin-top:6px">6 维 %(s6)d/100(%(g6)s) · 内容工程 %(sce)s/100(%(gce)s)%(qc)s · 为何没被引用:%(verdict)s</div>
</div>

<div class="card"><h2>统一行动清单(按杠杆位排序:证据层 &gt; 收录 &gt; 结构 &gt; 投放 &gt; 监测)</h2>
<ol class="actions">%(actions)s</ol></div>

<div class="card"><h2>信源策略 · 分层投放</h2>%(tiers)s</div>

<div class="card"><h2>监测采集闭环</h2>
<div style="font-size:13px;color:#555">%(protocol)s</div>
<div style="font-size:13px;color:#555;margin-top:6px"><b>要去问的 prompt(节选):</b></div>
<ul class="prompts">%(prompts)s</ul>
<div style="font-size:12px;color:#888">采集回的 AI 回答喂 <code>geo_cli measure --input records.json</code> 闭环。</div>
</div>

<div class="note">%(note)s</div>
</body></html>""" % {
        "title": title,
        "market": e(pb["market"]),
        "engines": e("、".join(pb["target_engines"]) or "(未指定)"),
        "color": color,
        "layer": e(b["bottleneck_layer"]),
        "conf": e(conf),
        "first": e(b["first_action"]),
        "bar6": _bar(s["total"], "#2b6cb0", "6 维评分 %d/100" % s["total"]),
        "barce": _bar(ce_["score"], "#e8833a", "内容工程 %s/100" % ce_["score"]),
        "barev": _bar(evid / 43 * 100, "#d73027",
                      "证据引用层 %s/43(权重最高的内容杠杆,方向性口径)" % evid),
        "s6": s["total"], "g6": e(s["grade"]),
        "sce": ce_["score"], "gce": e(ce_["grade"]), "qc": qc_html,
        "verdict": e(pb["diagnosis"]["verdict"]),
        "actions": "".join(actions),
        "tiers": "".join(tiers_html) or '<div style="color:#888">(未指定引擎)</div>',
        "protocol": e(pb["measure_kit"]["protocol"]),
        "prompts": prompt_lis or "<li>(未给品牌/品类)</li>",
        "note": e(pb["note"]),
    }
