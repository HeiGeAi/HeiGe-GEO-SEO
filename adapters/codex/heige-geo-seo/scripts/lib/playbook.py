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
