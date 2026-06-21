"""改写指令编译器 + GEO Brief 生成器。

把"哪项不达标 → 该用哪个 GEO 方法 → 生成哪条精确改写指令"映射成确定性输出,
产出可直接喂任意 LLM 执行的改写指令包(LLM 无关)。这是 HeiGe-GEO-SEO 相对
Surfer/Jasper/Writesonic(改写锁死在自家黑盒)的差异化护城河。

参考 AutoGEO-API 的"规则集嵌指令"思路,但规则来自 9 方法实测权重 + 6 维评分卡。
纯标准库,确定性。
"""

from . import anti_ai


# check id -> 改写动作(method 来自 methodology/geo-methods.md,lift 为论文实测)
_ACTION_MAP = {
    "D1": {"method": ["加统计 Statistics", "标注来源 Cite Sources"], "lift": "+30.7%",
           "action": "每 100 词补到 ≥4 个可抽取事实,改成带真实数字、可验证的陈述;数据必须有具名来源,素材不足就标[需补真实数据],绝不编造"},
    "D2": {"method": ["答案前置 Answer-First"], "lift": "+27%",
           "action": "把本节开头改写成 40-60 词的自包含直接答案,主谓宾齐全,不依赖上文指代,能被整句抽走当一句话用"},
    "D3": {"method": ["流畅度 Fluency"], "lift": "+24.2%",
           "action": "把平均句长调到 15-20 词,长短句交替做 burstiness 扰动"},
    "D4": {"method": ["流畅度 Fluency"], "lift": "可抽取率",
           "action": "正文密度调到 800-1500 词区间,过长砍掉枝节,保持短而密"},
    "D5": {"method": ["加统计 Statistics", "标注来源 Cite Sources"], "lift": "+40%",
           "action": "每个论断配 1 个真实可验证数字 + 1 个带外链的具名来源"},
    "C1": {"method": ["结构化 FAQPage"], "lift": "2.7x 引用率",
           "action": "把内容里用户真实会问的问答对抽成 FAQPage JSON-LD(geo_cli schema --type faqpage),页面也要有对应可见问答文本"},
    "C2": {"method": ["实体标注"], "lift": "AI Mode 引用页占 76%",
           "action": "补 Article + Organization schema(geo_cli schema --type organization),Article 配 Person 作者的 @id 可信链"},
    "C3": {"method": ["实体标注"], "lift": "可解析度",
           "action": "给关键 schema 补到 ≥5 个真实属性,别只填 name/type"},
    "E1": {"method": ["结构化"], "lift": "可解析度",
           "action": "改成单一 H1 + 不跳级的 H2/H3 层级,每个小标题语义化(写清这节回答什么)"},
    "E2": {"method": ["结构化"], "lift": "列表抽取率高于散文",
           "action": "把可列举内容改成 <ul>/<ol> 列表,把任何 A vs B 对比改成 <table> 表格带表头"},
    "E3": {"method": ["独立定义", "结构化"], "lift": "定义类查询命中",
           "action": "关键术语首次出现加'X 是……'定义块;把小标题改成用户问句(X 是什么/怎么做 Y/X 和 Y 的区别)"},
    "E4": {"method": ["语义三元组"], "lift": "可引用单元",
           "action": "把句子改成清晰主-谓-宾结构,让 AI 能拆成离散可引用的事实单元"},
    "F1": {"method": ["权威信号"], "lift": "署名提升引用意愿",
           "action": "加具名作者 + 链到独立作者页 + Person schema(geo_cli schema --type person)"},
    "F2": {"method": ["实体优化"], "lift": "进知识图谱检索路径",
           "action": "补 sameAs 外链到 Wikipedia/Wikidata/LinkedIn/Crunchbase,没有 Wikidata Q-ID 在这条路径上隐形"},
    "F3": {"method": ["实体一致性"], "lift": "实体可识别",
           "action": "统一全站品牌名/创始人/产品名的措辞,消除跨页不一致"},
    "F4": {"method": ["新鲜度"], "lift": "AI 偏好新鲜内容",
           "action": "标注 dateModified(ISO 8601 带时区)并实际更新内容,7-14 天回看一次"},
}

# 引擎差异化改写分叉(同内容按目标引擎微调,来自竞品实证)
_ENGINE_FORK = {
    "perplexity": "主攻 Perplexity:开头放 134-167 词自包含答案胶囊 + 加可验证引用 + 建命名作者实体",
    "claude": "主攻 Claude:加显式'局限性'段落(实测 +1.7x 引用)+ 去营销腔 + 多源验证语气",
    "gemini": "主攻 Gemini:H2 改成口语化问句(question-forward)+ 强调全站主题覆盖而非单页",
    "chatgpt": "主攻 ChatGPT:前 150-300 字直给答案 + 重域名声誉与可读性(走 Bing 索引,见效 6-12 周)",
    "豆包": "主攻豆包:内容铺进今日头条/抖音生态,带行业话题标签,务必有数据有案例(豆包拒绝无来源内容)",
    "元宝": "主攻腾讯元宝:走微信公众号(独家信源,占比约10%),服务号/小程序结构化信息",
    "文心": "主攻文心:进百家号/百度百科,绑百度搜索索引",
    "deepseek": "主攻 DeepSeek:重时效,进搜狐/百度百科/网易门户,被 Bing/博查 收录",
}


def compile_instructions(score_result, target_engine=None, lang="zh"):
    """吃 scoring.score_document 的结果,产出改写指令包。
    只对失分/部分达标的内容类检查(C/D/E/F)出指令,文件类(A/B)交给生成器。"""
    packs = []
    for dim in score_result.get("dimensions", []):
        if dim["key"] in ("A", "B"):
            continue
        for chk in dim["checks"]:
            if chk["status"] == "pass":
                continue
            mapping = _ACTION_MAP.get(chk["id"])
            if not mapping:
                continue
            pack = {
                "check": chk["id"],
                "dimension": dim["key"],
                "status": chk["status"],
                "earned": chk["earned"],
                "weight": chk["weight"],
                "diagnosis": chk["name"] + ("(" + chk["note"] + ")" if chk["note"] else ""),
                "geo_method": mapping["method"],
                "expected_lift": mapping["lift"],
                "rewrite_instruction": mapping["action"],
                "constraints": ["不改事实", "不堆关键词", "字数 ±10%", "引语/统计/引用只用真实素材"],
                "anti_ai_clause": anti_ai.constraint_clause(lang),
            }
            if target_engine:
                fork = _ENGINE_FORK.get(target_engine.lower())
                if fork:
                    pack["engine_fork"] = fork
            packs.append(pack)
    # 按权重缺口排序,先修影响最大的
    packs.sort(key=lambda p: (p["weight"] - p["earned"]), reverse=True)
    return {
        "source_score": score_result.get("score"),
        "target_engine": target_engine,
        "instruction_count": len(packs),
        "instructions": packs,
        "note": "本指令包 LLM 无关,可直接喂任意大模型执行。引语/统计/引用只用真实素材,改写后须过 GEU 护栏。",
    }


def render_markdown(pack_result):
    """把指令包渲染成人类可读 markdown。"""
    out = ["# GEO 改写指令包", ""]
    out.append("源页面评分: %s | 目标引擎: %s | 共 %d 条指令" % (
        pack_result.get("source_score"), pack_result.get("target_engine") or "通用",
        pack_result["instruction_count"]))
    out.append("")
    out.append("> " + pack_result["note"])
    out.append("")
    for i, p in enumerate(pack_result["instructions"], 1):
        out.append("## %d. [%s] %s" % (i, p["check"], p["diagnosis"]))
        out.append("- **方法**: %s" % "、".join(p["geo_method"]))
        out.append("- **预期提升**: %s" % p["expected_lift"])
        out.append("- **改写指令**: %s" % p["rewrite_instruction"])
        if p.get("engine_fork"):
            out.append("- **引擎分叉**: %s" % p["engine_fork"])
        out.append("- **约束**: %s" % "、".join(p["constraints"]))
        out.append("- **%s**" % p["anti_ai_clause"])
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------
# GEO Content Brief 生成器(GEO-first,区别于市面 SEO brief)
# --------------------------------------------------------------------------
def gen_geo_brief(topic, primary_question, sections, entities=None,
                  paa_questions=None, target_engine=None, schema_types=None,
                  lang="zh"):
    """以可被引用性为骨架的 GEO brief。
    sections: list of H2 小标题(应为用户问句形态)。"""
    schema_types = schema_types or ["Article", "FAQPage", "Organization"]
    brief = {
        "topic": topic,
        "target_engine": target_engine,
        "h1_suggestion": topic,
        "tldr_answer": "[40-60 词自包含直接答案,回答:%s]" % primary_question,
        "sections": [],
        "entity_coverage": [],
        "paa_questions": paa_questions or [],
        "anchor_quota": {
            "statistics": max(2, len(sections)),
            "citations": max(2, len(sections)),
            "quotations": 1,
            "note": "统计/引用按 9 方法权重配额:加统计+30.7%、标注来源+28.2%、加引语+41.2%,均须真实素材",
        },
        "schema_types": schema_types,
        "anti_ai_constraints": anti_ai.constraints(lang),
    }
    for s in sections:
        brief["sections"].append({
            "h2": s,
            "answer_first_words": "40-60",
            "must_include": "1 个可验证统计 + 1 个具名来源 + 1 个清晰主谓宾定义句",
            "chunk": "本节独立成块,自包含,不依赖前文指代",
        })
    for e in (entities or []):
        brief["entity_coverage"].append({
            "entity": e,
            "first_definition_at": "首次出现处给'X 是……'定义",
            "sameas_hint": "若是品牌/机构,补 sameAs 到 Wikipedia/Wikidata/LinkedIn",
        })
    if target_engine:
        fork = _ENGINE_FORK.get(target_engine.lower())
        if fork:
            brief["engine_note"] = fork
    return brief


def render_brief_markdown(brief):
    out = ["# GEO Content Brief: %s" % brief["topic"], ""]
    out.append("目标引擎: %s" % (brief.get("target_engine") or "通用"))
    out.append("")
    out.append("## H1\n%s\n" % brief["h1_suggestion"])
    out.append("## TL;DR 答案块\n%s\n" % brief["tldr_answer"])
    out.append("## 章节(每节首段即答案)")
    for s in brief["sections"]:
        out.append("- **%s**(answer-first %s 词):%s,%s" % (
            s["h2"], s["answer_first_words"], s["must_include"], s["chunk"]))
    out.append("")
    if brief["entity_coverage"]:
        out.append("## 必须覆盖的实体")
        for e in brief["entity_coverage"]:
            out.append("- %s:%s;%s" % (e["entity"], e["first_definition_at"], e["sameas_hint"]))
        out.append("")
    if brief["paa_questions"]:
        out.append("## 必答问句(question-forward H2)")
        for q in brief["paa_questions"]:
            out.append("- %s" % q)
        out.append("")
    aq = brief["anchor_quota"]
    out.append("## 锚点配额")
    out.append("- 统计 ≥%d 处、引用 ≥%d 处、引语 ≥%d 处" % (
        aq["statistics"], aq["citations"], aq["quotations"]))
    out.append("- %s" % aq["note"])
    out.append("")
    out.append("## 该上的 Schema\n%s\n" % "、".join(brief["schema_types"]))
    if brief.get("engine_note"):
        out.append("## 引擎差异化\n%s\n" % brief["engine_note"])
    out.append("## 反 AI 味约束")
    for c in brief["anti_ai_constraints"]:
        out.append("- %s" % c)
    return "\n".join(out)
