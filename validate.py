#!/usr/bin/env python3
"""HeiGe-GEO-SEO 完整性自检(确定性 audit)。

检查项:
  1. manifest.json 引用的所有资源文件都存在
  2. source/ 下所有 [[wikilink]] 都能解析到真实文件
  3. 脚本可导入并能跑出合理评分(好页面≥70,差页面触发否决)
  4. 构建产物存在且与 build-manifest 一致(四套适配齐全)
  5. 文风红线:source 正文不含中文破折号

任一失败,退出码 1,供 CI 硬卡。
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "source")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

errors = []
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        errors.append(msg)
    return cond


# 1. manifest references exist -------------------------------------------
def check_manifest():
    with open(os.path.join(SOURCE, "manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    for key in ("knowledge", "methodology", "workflow", "templates"):
        for rel in m[key]:
            ok(os.path.isfile(os.path.join(SOURCE, rel)),
               "manifest 引用缺失: %s" % rel)
    ok(os.path.isfile(os.path.join(ROOT, m["scripts"]["entry"])),
       "脚本入口缺失: %s" % m["scripts"]["entry"])
    return m


# 2. wikilinks resolve ----------------------------------------------------
def md_files():
    out = []
    for base, _d, fs in os.walk(SOURCE):
        for f in fs:
            if f.endswith(".md"):
                out.append(os.path.join(base, f))
    return out


def build_stem_index():
    idx = {}
    for p in md_files():
        idx.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    return idx


def check_wikilinks():
    idx = build_stem_index()
    link_re = re.compile(r"\[\[([^\]]+)\]\]")
    for p in md_files():
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        for raw in link_re.findall(text):
            target = raw.split("|")[0].strip()
            base = os.path.basename(target)
            stem = os.path.splitext(base)[0]
            if "/" in target:
                resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
                found = (os.path.isfile(resolved) or os.path.isfile(resolved + ".md")
                         or stem in idx)
            else:
                found = stem in idx
            ok(found, "未解析的 wikilink [[%s]] in %s" %
               (raw, os.path.relpath(p, ROOT)))


# 3. scripts run ----------------------------------------------------------
def check_scripts():
    try:
        from lib import htmldoc, scoring  # noqa
    except Exception as e:  # pragma: no cover
        ok(False, "脚本导入失败: %s" % e)
        return
    good = os.path.join(ROOT, "tests", "fixtures", "good_page.html")
    poor = os.path.join(ROOT, "tests", "fixtures", "poor_page.html")
    if ok(os.path.isfile(good), "缺好页面夹具") and ok(os.path.isfile(poor), "缺差页面夹具"):
        rg = scoring.score_document(htmldoc.from_file(good))
        ok(rg["score"] >= 70, "好页面评分异常(<70): %d" % rg["score"])
        rp = scoring.score_document(htmldoc.from_file(poor))
        ok(rp["vetoes"], "差页面应触发否决项却没有")
        ok(rp["score"] <= 60, "差页面评分异常(>60): %d" % rp["score"])


# 4. build artifacts ------------------------------------------------------
def check_build(manifest):
    bm_path = os.path.join(ROOT, "adapters", "build-manifest.json")
    if not ok(os.path.isfile(bm_path), "未构建:缺 adapters/build-manifest.json(先跑 build.py)"):
        return
    with open(bm_path, encoding="utf-8") as fh:
        bm = json.load(fh)
    for adapter in manifest["adapters"]:
        ok(adapter in bm["adapters"], "构建缺适配: %s" % adapter)
        pkg = os.path.join(ROOT, "adapters", adapter, "heige-geo-seo")
        ok(os.path.isdir(pkg), "适配目录缺失: %s" % adapter)
        ok(os.path.isfile(os.path.join(pkg, "scripts", "geo_cli.py")),
           "%s 适配缺 scripts/geo_cli.py" % adapter)
        for d in ("knowledge", "methodology", "workflow", "templates"):
            ok(os.path.isdir(os.path.join(pkg, d)), "%s 适配缺 %s/" % (adapter, d))


# 5. style red line -------------------------------------------------------
def check_style():
    for p in md_files():
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        ok("—" not in text, "正文含破折号(—),违反文风红线: %s" %
           os.path.relpath(p, ROOT))


def main():
    m = check_manifest()
    check_wikilinks()
    check_scripts()
    check_build(m)
    check_style()
    print("完整性自检:跑了 %d 项检查" % checks)
    if errors:
        print("发现 %d 个问题:" % len(errors))
        for e in errors:
            print("  X " + e)
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
