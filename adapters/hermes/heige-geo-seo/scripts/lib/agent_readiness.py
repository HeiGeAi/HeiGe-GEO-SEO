"""WebMCP / agentic task readiness 静态审计。

W3C WebMCP 草案 2026.02 落地,让 AI agent 直接在站上完成 下单/注册/预约/留资。
站上能完成、你站上不能,就在成交瞬间丢单。市面 checker 都是在线服务,
我方做离线静态审计:吃站点 HTML,审表单 agent 就绪度,出整改清单。不碰浏览器执行。
纯标准库,基于 htmldoc 的原始 HTML 正则分析。
"""

import re


_KEY_ACTIONS = ["下单", "购买", "注册", "预约", "留资", "提交", "checkout",
                "buy", "sign up", "signup", "register", "book", "subscribe"]


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

    # inputs with labels / name
    inputs = re.findall(r"<input\b[^>]*>", raw, re.IGNORECASE)
    named = [i for i in inputs if re.search(r'\bname\s*=', i, re.IGNORECASE)]
    labeled = bool(re.search(r"<label\b", raw, re.IGNORECASE))
    add("input 有稳定 name 属性", inputs and len(named) >= max(1, len(inputs) // 2), 15,
        "每个 input 给稳定的 name/id,别用随机生成的 class hash")
    add("表单字段有 <label>", labeled or not has_form, 15,
        "每个输入配 <label for>,agent 靠 label 理解字段语义")

    # WebMCP declarative attributes
    has_toolname = bool(re.search(r'\btoolname\s*=', raw, re.IGNORECASE))
    has_tooldesc = bool(re.search(r'\btooldescription\s*=', raw, re.IGNORECASE))
    add("已加 WebMCP 声明式属性(toolname/tooldescription)", has_toolname and has_tooldesc, 20,
        "给关键 <form> 加 toolname 和 tooldescription 两个属性,声明这是个 agent 可调用的工具")

    # ARIA
    has_aria = bool(re.search(r'\b(aria-label|role)\s*=', raw, re.IGNORECASE))
    add("有 ARIA 标签/角色", has_aria, 10,
        "给交互元素加 aria-label / role,提升 agent 与无障碍可读性")

    # key actions discoverable
    action_found = any(a in raw for a in _KEY_ACTIONS)
    add("关键动作可被机器识别", action_found, 20,
        "把下单/注册/预约等关键动作用清晰文案+按钮标注,盘点 5-10 个关键动作")

    total = sum(c["weight"] for c in checks)
    earned = sum(c["earned"] for c in checks)
    score = round(earned / total * 100) if total else 0
    return {
        "form_count": len(forms),
        "score": score,
        "grade": "就绪" if score >= 80 else ("部分就绪" if score >= 50 else "未就绪"),
        "checks": checks,
        "note": "WebMCP 标准 2026.02 落地,Chrome/Edge 原生支持瞄准 2026 下半年。提前就绪占先发位。",
    }
