"""Token 预算估算器(近似)。

AEO 基础设施一环:答案前置避免被截断、内容分块守预算、llms-full 拼接别超量。
评分卡 D4 用的是词数,词数 != token(中文 1 字约 1-2 token,模型 tokenizer 各异)。
这里给一个纯标准库的粗估,明确标"近似,精确请用 tiktoken"。
"""

import re


# 经验系数(粗估):中文每字约 1.6 token,英文每词约 1.3 token,数字/标点另算
_CJK_PER_TOKEN = 1.6
_WORD_PER_TOKEN = 1.3


def estimate(text):
    """近似 token 数。"""
    text = text or ""
    cjk = len(re.findall(r"[〇㐀-䶿一-鿿]", text))
    words = len(re.findall(r"[A-Za-z][A-Za-z'-]*", text))
    nums = len(re.findall(r"\d+", text))
    puncts = len(re.findall(r"[,.;:!?，。；：！？、]", text))
    approx = round(cjk * _CJK_PER_TOKEN + words * _WORD_PER_TOKEN + nums + puncts * 0.5)
    return approx


def check(text, budget):
    """给定预算判是否超。budget 为目标 token 上限。"""
    tok = estimate(text)
    return {
        "approx_tokens": tok,
        "budget": budget,
        "within_budget": tok <= budget,
        "over_by": max(0, tok - budget),
        "note": "近似估算(中文×1.6/英文词×1.3),精确请用各模型官方 tokenizer(如 tiktoken)。"
                "答案前置:把核心结论放进前 ~300 token,避免被上下文窗口截断。",
    }
