#!/usr/bin/env python3
"""HeiGe-GEO-SEO 零依赖转译构建链。

把 source/ 这份 canonical 单源转译成多个 AI Agent 运行时的自包含适配包:
  - claude-code   Claude Code 技能(SKILL.md + 资源 + 脚本)
  - codex         OpenAI Codex(AGENTS.md 指令 + 资源 + 脚本)
  - openclaw      OpenClaw(SKILL.md + openclaw.json + 资源 + 脚本)
  - hermes        Hermes(skill.md + 资源 + 脚本)

每个适配包都自包含、可独立分发。构建产物记进 adapters/build-manifest.json,
含每个文件的 sha256,供 CI 校验一致性。仅用 Python 标准库。
"""

import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "source")
SCRIPTS = os.path.join(ROOT, "scripts")
ADAPTERS = os.path.join(ROOT, "adapters")

RESOURCE_DIRS = ["knowledge", "methodology", "workflow", "templates"]


def load_manifest():
    with open(os.path.join(SOURCE, "manifest.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def split_frontmatter(skill_md):
    """Return (frontmatter_text, body_text) from a SKILL.md file."""
    if skill_md.startswith("---"):
        parts = skill_md.split("---", 2)
        if len(parts) == 3:
            return parts[1].strip(), parts[2].strip()
    return "", skill_md.strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# per-runtime entry file renderers
# --------------------------------------------------------------------------
def _trigger_block(manifest):
    zh = "、".join(manifest["triggers"]["zh"])
    en = ", ".join(manifest["triggers"]["en"])
    return "**中文触发词**:%s\n\n**English triggers**: %s" % (zh, en)


def render_claude_code(manifest, fm, body):
    # Claude Code uses the SKILL.md verbatim (YAML frontmatter + body).
    content = "---\n%s\n---\n\n%s\n" % (fm, body)
    return [("SKILL.md", content)]


def render_codex(manifest, fm, body):
    # Codex reads AGENTS.md as agent instructions (no CC YAML frontmatter).
    head = "# %s (Codex Skill)\n\n" % manifest["displayName"]
    head += manifest["description_zh"] + "\n\n"
    head += "## 触发\n\n" + _trigger_block(manifest) + "\n\n"
    head += "## 能力\n\n" + "\n".join("- " + c for c in manifest["capabilities"]) + "\n\n"
    head += "---\n\n"
    return [("AGENTS.md", head + body + "\n")]


def render_openclaw(manifest, fm, body):
    # OpenClaw runs Claude-style skills; keep SKILL.md + a small manifest.
    content = "---\n%s\n---\n\n%s\n" % (fm, body)
    oc = {
        "name": manifest["name"],
        "displayName": manifest["displayName"],
        "version": manifest["version"],
        "entry": "SKILL.md",
        "triggers": manifest["triggers"],
        "scripts": manifest["scripts"],
    }
    return [("SKILL.md", content),
            ("openclaw.json", json.dumps(oc, ensure_ascii=False, indent=2) + "\n")]


def render_hermes(manifest, fm, body):
    head = "# %s\n\n" % manifest["displayName"]
    head += "> %s\n\n" % manifest["description_zh"]
    head += "## 触发\n\n" + _trigger_block(manifest) + "\n\n---\n\n"
    return [("skill.md", head + body + "\n")]


RENDERERS = {
    "claude-code": render_claude_code,
    "codex": render_codex,
    "openclaw": render_openclaw,
    "hermes": render_hermes,
}


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def copytree(src, dst):
    for base, _dirs, files in os.walk(src):
        if "__pycache__" in base:
            continue
        rel = os.path.relpath(base, src)
        target_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            if f.endswith(".pyc"):
                continue
            shutil.copy2(os.path.join(base, f), os.path.join(target_dir, f))


def build():
    manifest = load_manifest()
    skill_md = read(os.path.join(SOURCE, "SKILL.md"))
    fm, body = split_frontmatter(skill_md)

    if os.path.isdir(ADAPTERS):
        shutil.rmtree(ADAPTERS)
    os.makedirs(ADAPTERS)

    build_record = {"name": manifest["name"], "version": manifest["version"],
                    "adapters": {}}

    for adapter in manifest["adapters"]:
        renderer = RENDERERS.get(adapter)
        if renderer is None:
            print("跳过未知运行时: %s" % adapter)
            continue
        pkg = os.path.join(ADAPTERS, adapter, "heige-geo-seo")
        os.makedirs(pkg, exist_ok=True)

        # 1) entry file(s)
        files_written = []
        for fname, content in renderer(manifest, fm, body):
            with open(os.path.join(pkg, fname), "w", encoding="utf-8") as fh:
                fh.write(content)
            files_written.append(fname)

        # 2) resources (knowledge/methodology/workflow/templates)
        for d in RESOURCE_DIRS:
            copytree(os.path.join(SOURCE, d), os.path.join(pkg, d))

        # 3) scripts (self-contained, shared logic)
        copytree(SCRIPTS, os.path.join(pkg, "scripts"))

        # 4) manifest copy
        shutil.copy2(os.path.join(SOURCE, "manifest.json"),
                     os.path.join(pkg, "manifest.json"))

        # 5) per-adapter install note
        with open(os.path.join(pkg, "INSTALL.md"), "w", encoding="utf-8") as fh:
            fh.write(install_note(adapter, manifest))

        # record file hashes
        recorded = {}
        for base, _dirs, fs in os.walk(pkg):
            if "__pycache__" in base:
                continue
            for f in fs:
                p = os.path.join(base, f)
                recorded[os.path.relpath(p, pkg)] = sha256(p)
        build_record["adapters"][adapter] = {
            "entry": files_written[0],
            "file_count": len(recorded),
            "files": recorded,
        }
        print("构建 %-12s -> %d 个文件" % (adapter, len(recorded)))

    with open(os.path.join(ADAPTERS, "build-manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(build_record, fh, ensure_ascii=False, indent=2)
    print("写入 adapters/build-manifest.json")
    return build_record


def install_note(adapter, manifest):
    name = manifest["displayName"]
    notes = {
        "claude-code": (
            "把本目录(heige-geo-seo/)放进 `~/.claude/skills/` 或项目 `.claude/skills/`,"
            "Claude Code 会按 SKILL.md 的 description 自动触发。\n\n"
            "脚本直接跑:`python3 scripts/geo_cli.py --help`"),
        "codex": (
            "把本目录放进 Codex 的 skills/ 或在项目根引用 AGENTS.md。"
            "Codex 读 AGENTS.md 作为 agent 指令。\n\n"
            "脚本直接跑:`python3 scripts/geo_cli.py --help`"),
        "openclaw": (
            "把本目录放进 OpenClaw 的技能目录,openclaw.json 描述入口与触发词,"
            "SKILL.md 为技能本体。\n\n"
            "脚本直接跑:`python3 scripts/geo_cli.py --help`"),
        "hermes": (
            "在 Hermes 中加载 skill.md 作为技能定义,资源在同目录 knowledge/ 等。\n\n"
            "脚本直接跑:`python3 scripts/geo_cli.py --help`"),
    }
    return "# %s · %s 适配包\n\n%s\n" % (name, adapter, notes.get(adapter, ""))


if __name__ == "__main__":
    build()
    sys.exit(0)
