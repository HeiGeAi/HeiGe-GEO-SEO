---
name: heige-geo-seo
version: 1.0.0
description: >-
  HeiGe-GEO-SEO 是一套面向中国市场优先的 GEO(生成式引擎优化)+ SEO 内容优化系统。当用户需要让内容/网页被
  AI 大模型(豆包、通义千问、DeepSeek、文心、腾讯元宝、ChatGPT、Perplexity、Claude、Gemini)抓取并引用、
  做 GEO 优化、做 AI 搜索优化、优化网页被 AI 引用、写能被 AI 引用的内容、配 robots.txt 给 AI 爬虫、生成 llms.txt、
  生成 schema 结构化数据、规划内容发布渠道矩阵、给网页架构 SEO/GEO 建议时使用。
  Trigger in English on: GEO, generative engine optimization, AEO, answer engine optimization, AI search
  optimization, "get cited by ChatGPT/Perplexity/AI", optimize content for AI engines, llms.txt, AI crawler
  robots.txt, schema for AI citation. 触发词:GEO优化、生成式引擎优化、AI搜索优化、让AI引用、被AI引用、AEO、
  让豆包/千问/DeepSeek引用我、GEO SEO、AI可见度、内容被大模型抓取。
---

# HeiGe-GEO-SEO · 中国优先的 GEO + SEO 优化系统

> 集 GEO 学术方法论(KDD 2024 / ICLR 2026 两篇论文)+ 工程化评分框架 + 中国大模型抓取逻辑于一体。
> 别的 GEO 工具只盯 ChatGPT/Perplexity,这套**先打豆包、千问、DeepSeek、文心、元宝**,海外作对照。

## 这套工具解决什么

让你的内容和网页被 AI 大模型抓取并引用。覆盖四件事:**给谁优化**(大模型分类)、**怎么被抓到**(抓取逻辑)、**发哪里曝光**(渠道矩阵)、**网页怎么建**(架构建议)。

## 核心原则(先记这几条)

1. **国内 GEO 是求收录 + 占平台游戏,海外 GEO 是配 robots.txt 游戏。** 两套打法别混用,见 `knowledge/02-crawler-logic.md`。
2. **按排名分流:** 排名靠后的页面激进上引用类方法(可冲 +100%),排名第一的页面慎用(会 -30%),见 `methodology/geo-methods.md`。
3. **合规红线:引语/统计/引用只用真实素材,永不编造。** Keyword Stuffing 永久禁用(它是负效果)。改写后跑 GEU 护栏。
4. **人不可被绕过:** Brief 的专家洞察槽位和质量门的 BLOCK 裁决两个 checkpoint 不能自动跳过。GEO 惩罚没有真实洞察的水文。

## 怎么用(按需选路径)

### 完整客户交付 → 走十阶段工作流

读 `workflow/stages.md`,从 01 Intake 到 10 Re-audit 全程。两个人工 checkpoint(04 专家洞察、07 质量门 BLOCK)不可绕过。

### 只优化一篇已有内容 → 轻量路径

03 基线打分 → 05 改写 → 07 质量门复评。

1. 用 `scripts/geo_score.py` 给原内容/页面打基线分(6 维 22 项)
2. 按 `methodology/geo-methods.md` 选改写方法(看内容域 + 搜索排名档位)
3. 改写,默认组合"流畅度 + 加统计",需要时叠"标注来源"
4. 重打分对比,跑 GEU 护栏(KPC 矛盾度不超阈值)
5. 出 before/after 评分报告

### 只要发布建议 → 读发布库

读 `knowledge/03-publishing-channels.md`,按目标 AI 引擎给一稿四态渠道矩阵。国内押生态多平铺,海外押 Reddit,知乎优先。

### 只要网页/技术建议 → 读架构库 + 跑生成脚本

读 `knowledge/04-webpage-architecture.md`,然后:

- `scripts/gen_robots.py` 生成最优 AI 爬虫 robots.txt(全放/只曝光不喂训练/国内求收录三种策略)
- `scripts/gen_schema.py` 生成 JSON-LD(Article/FAQPage/HowTo/Product)
- `scripts/gen_llms_txt.py` 生成 llms.txt(注意:营销站别投,开发者工具才做)

## 资源地图

| 你要做什么 | 读这个 |
|---|---|
| 判断给哪个 AI 优化 | `knowledge/01-llm-landscape.md` |
| 搞清楚 AI 怎么抓到内容 | `knowledge/02-crawler-logic.md` |
| 决定内容发哪些渠道 | `knowledge/03-publishing-channels.md` |
| 给网页架构建议 | `knowledge/04-webpage-architecture.md` |
| 选改写方法 | `methodology/geo-methods.md` |
| 给内容/页面打分 | `methodology/scoring-card.md` |
| 跑完整流程 | `workflow/stages.md` |
| 输出交付物 | `templates/` 下四个模板 |
| 跑确定性工具 | `scripts/` 下 CLI:`python3 scripts/geo_cli.py --help` |

## 脚本速查(零依赖,仅 Python 标准库)

```bash
# 给一个 HTML 文件或 URL 打 GEO 可被引用度分
python3 scripts/geo_cli.py score --input page.html

# 生成 AI 爬虫 robots.txt
python3 scripts/geo_cli.py robots --strategy expose-only --sitemap https://example.com/sitemap.xml

# 生成 JSON-LD schema
python3 scripts/geo_cli.py schema --type article --title "标题" --author "张三" --org "示例科技"

# 从 URL 列表生成 llms.txt
python3 scripts/geo_cli.py llms --site "示例科技" --summary "一句话简介" --links links.txt
```

## 不要做的事(诚实边界)

- 不编造引语、统计、引用。素材不足就让用户补,产出待补清单。
- 不把 llms.txt 当排名杠杆向用户承诺。它是 B2A 基础设施,营销站做了基本无效。
- 不用一套规则打所有引擎。豆包和 ChatGPT 的偏好不一样,按目标引擎调。
- 不绕过两个人工 checkpoint。

---

兼容 Claude Code / Codex / OpenClaw / Hermes,由单源转译。开源协议 MIT。
