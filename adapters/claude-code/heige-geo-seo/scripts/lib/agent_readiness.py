"""WebMCP / agentic task readiness 静态审计。

W3C WebMCP 草案 2026.02 落地,让 AI agent 直接在站上完成 下单/注册/预约/留资。
站上能完成、你站上不能,就在成交瞬间丢单。市面 checker 都是在线服务,
我方做离线静态审计:吃站点 HTML,审表单 agent 就绪度 + agent-hostile 反模式,出整改清单。
不碰浏览器执行。纯标准库,基于 htmldoc 的原始 HTML 正则分析。

诚实红线:WebMCP declarative 属性名 2026 年内仍在变,本审计按 W3C 2026.02 草案方向给建议,
imperative `navigator.modelContext.registerTool()` 才是当前草案重心;落地前用真 Chrome 核对。
当前主力 browsing agent(Operator/Claude Computer Use/Gemini)走 computer-use 视觉路线,
所以"无反模式 + 干净语义"今天就有效,WebMCP 标记是押注下半年原生支持。
"""

import re


_KEY_ACTIONS = ["下单", "购买", "注册", "预约", "留资", "提交", "checkout",
                "buy", "sign up", "signup", "register", "book", "subscribe"]


def _antipatterns(raw):
    """agent-hostile 反模式:这些今天就会让真实 agent(computer-use)任务失败。"""
    found = []

    def hit(pat, name, fix):
        if re.search(pat, raw, re.IGNORECASE):
            found.append({"pattern": name, "fix": fix})

    hit(r"(recaptcha|hcaptcha|cf-turnstile|g-recaptcha|geetest|易盾|dun\.163|"
        r"aliyun.*captcha|防水墙|tcaptcha|滑动验证|点选验证|nc_iconfont)",
        "CAPTCHA 验证码(含国内极验/易盾/防水墙)",
        "关键流程别强制 CAPTCHA,或给 agent 友好的无验证码路径")
    hit(r'<input\b[^>]*type\s*=\s*["\']?file', "file 上传输入",
        "关键动作里有 <input type=file>,agent 没法选本地文件,改其它输入方式")
    hit(r"(canvas|jquery-ui|datepicker|fullcalendar)", "canvas/自定义控件",
        "日历/控件用 canvas 或自定义 JS,无 <input type=date> 兜底,agent 操作不了")
    # placeholder 当 label(有 placeholder 但全程无 label)
    if re.search(r"placeholder\s*=", raw, re.IGNORECASE) and not re.search(r"<label\b", raw, re.IGNORECASE):
        found.append({"pattern": "placeholder 当 label", "fix": "用 <label for> 而非仅 placeholder,agent 靠 label 理解字段"})
    hit(r"(必须先注册|请先登录|登录后才能|sign\s*up\s*to\s*continue|create an account to)",
        "强制注册墙", "关键动作前强制建账号,给 guest/游客流程,别在动作前竖墙")
    return found


def audit(doc):
    raw = doc.raw
    forms = re.findall(r"<form\b[^>]*>(.*?)</form>", raw, re.IGNORECASE | re.DOTALL)
    checks = []

    def add(name, ok, weight, fix):
        checks.append({"name": name, "status": "pass" if ok else "fail",
                       "weight": weight, "earned": weight if ok else 0,
                       "fix": "" if ok else fix})

    has_form = len(forms) > 0
    add("存在语义 <form> 表单", has_form, 20,
        "关键动作用真正的 <form> 包裹,别用纯 div+JS,agent 才能识别")

    inputs = re.findall(r"<input\b[^>]*>", raw, re.IGNORECASE)
    named = [i for i in inputs if re.search(r'\bname\s*=', i, re.IGNORECASE)]
    labeled = bool(re.search(r"<label\b", raw, re.IGNORECASE))
    add("input 有稳定 name 属性", inputs and len(named) >= max(1, len(inputs) // 2), 15,
        "每个 input 给稳定的 name/id,别用随机生成的 class hash")
    add("表单字段有 <label>", labeled or not has_form, 15,
        "每个输入配 <label for>,agent 靠 label 理解字段语义")

    # agent 可调用声明:declarative(toolname/tooldescription/data-mcp-*)或 imperative(registerTool)
    has_decl = bool(re.search(r'\b(toolname|tooldescription|data-mcp-\w+)\s*=', raw, re.IGNORECASE))
    has_imperative = bool(re.search(r"(navigator\.modelContext|registerTool|navigator\.mcpActions)", raw, re.IGNORECASE))
    add("已加 agent 可调用声明(declarative 或 imperative)", has_decl or has_imperative, 20,
        "二选一:declarative 给关键 <form> 加属性(属性名未定稿,可用 data-mcp-* 占位),"
        "或 imperative 用 navigator.modelContext.registerTool() 注册(草案重心)。落地前用真 Chrome 核对当前拼写")

    has_aria = bool(re.search(r'\b(aria-label|role)\s*=', raw, re.IGNORECASE))
    add("有 ARIA 标签/角色", has_aria, 10,
        "给交互元素加 aria-label / role,提升 agent 与无障碍可读性")

    action_found = any(a in raw for a in _KEY_ACTIONS)
    add("关键动作可被机器识别", action_found, 20,
        "把下单/注册/预约等关键动作用清晰文案+按钮标注,盘点 5-10 个关键动作")

    total = sum(c["weight"] for c in checks)
    earned = sum(c["earned"] for c in checks)
    score = round(earned / total * 100) if total else 0
    antipatterns = _antipatterns(raw)
    return {
        "form_count": len(forms),
        "score": score,
        "grade": "就绪" if score >= 80 else ("部分就绪" if score >= 50 else "未就绪"),
        "checks": checks,
        "imperative_detected": has_imperative,
        "antipatterns": antipatterns,
        "antipattern_count": len(antipatterns),
        "antipattern_note": "反模式为正则启发式,可能误报(如 canvas 撞类名),以人工复核为准;"
                            "宁可错报不漏报危险动作。",
        "note": "WebMCP 标准 2026.02 落地,Chrome/Edge 原生支持瞄准下半年。反模式是今天就让 "
                "computer-use agent(Operator/Claude/Gemini)任务失败的硬阻断,优先清;"
                "WebMCP 标记是押注未来原生支持。declarative 属性名未定稿,落地前核对真 Chrome。",
    }
