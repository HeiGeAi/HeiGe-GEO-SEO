"""Core Web Vitals 评估(对照 2026 阈值)。

CWV(LCP/INP/CLS)是 Google 明确排名信号。**field data 无法离线测**(需真实用户/
PageSpeed Insights),工具不臆造:你把 PSI 或 CrUX 的数值喂进来,这里对照阈值判优劣。
纯标准库,诚实边界。
"""

_THRESHOLDS = {
    "lcp": (2.5, 4.0, "s", "最大内容绘制,首屏主内容多快出现"),
    "inp": (200, 500, "ms", "交互到下次绘制,点击多快有反馈"),
    "cls": (0.1, 0.25, "", "累积布局偏移,页面跳不跳"),
}


def assess(metrics):
    """metrics: {'lcp': 秒, 'inp': 毫秒, 'cls': 数值}。任一缺省标 unknown。"""
    out = {}
    overall = "good"
    for k, (good, poor, unit, desc) in _THRESHOLDS.items():
        v = metrics.get(k)
        if v is None:
            out[k] = {"value": None, "rating": "unknown", "desc": desc,
                      "note": "未提供,从 PageSpeed Insights / CrUX field data 取"}
            if overall != "poor":
                overall = "unknown"
            continue
        if v <= good:
            rating = "good"
        elif v <= poor:
            rating = "needs-improvement"
            if overall == "good":
                overall = "needs-improvement"
        else:
            rating = "poor"
            overall = "poor"
        out[k] = {"value": v, "unit": unit, "rating": rating,
                  "good_threshold": good, "poor_threshold": poor, "desc": desc}
    return {
        "metrics": out,
        "overall": overall,
        "note": "CWV 是 field data(真实用户),工具不离线测,数值请从 PageSpeed Insights / "
                "Search Console 的 CrUX 取;lab 优化方向:SSR/静态、关键 CSS 内联、图片 WebP+懒加载、JS 延迟。",
    }
