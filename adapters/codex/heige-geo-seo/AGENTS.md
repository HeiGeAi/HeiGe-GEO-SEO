# HeiGe-GEO-SEO (Codex Skill)

中国市场优先的 GEO(生成式引擎优化)+ SEO 内容优化系统。诊断 → 产出 → 度量全链路。让内容和网页被豆包、通义千问、DeepSeek、文心、腾讯元宝、ChatGPT、Perplexity、Claude、Gemini 抓取并引用。

## 触发

**中文触发词**:GEO优化、生成式引擎优化、AI搜索优化、让AI引用、被AI引用、AEO、答案引擎优化、让豆包引用我、让千问引用我、让DeepSeek引用我、GEO SEO、AI可见度、内容被大模型抓取、配AI爬虫robots、生成llms.txt、网页被AI引用、做SEO和GEO、改写指令、share of voice、为什么没被AI引用、AI可见度监控、prompt集、GEO brief

**English triggers**: GEO, generative engine optimization, AEO, answer engine optimization, AI search optimization, get cited by ChatGPT, get cited by Perplexity, optimize content for AI engines, llms.txt, AI crawler robots.txt, schema for AI citation, AI visibility, share of voice, rewrite for GEO, WebMCP readiness, AI citation attribution

## 能力

- 大模型分类与引用行为判断
- 中国优先的 AI 抓取逻辑诊断
- 内容发布渠道矩阵与曝光建议(含新榜信源权重表)
- 平台发布推荐引擎(给目标引擎推荐发哪几个平台权重最高,中国新榜实证+海外引用研究)
- 全球场景:海外 11 引擎(检索地基三套)+ 20+ 平台权重矩阵 + 逐平台发布 SOP + B2B/B2C 分流 + 多语言
- 中外双轨爬虫归因(区分国内vs海外引擎,分训练/检索/用户触发,标 Grok 等 UA 盲区)
- SEO+GEO 网页架构与代码级建议
- GEO 改写方法(9 方法 + 排名分流 + 域映射 + GEU 护栏)
- GEO 可被引用度评分(6 维 22 项)
- 改写指令编译器(吃打分→出可喂任意 LLM 的改写指令包,LLM 无关)
- GEO Content Brief 生成器 + 反 AI 味约束库
- 「为何没被引用」7 根因诊断器
- buyer prompt 集生成 + Share of Voice 度量(三公式+基准阈值+采样置信度)
- GEO 归因检测(GA4 渠道组正则+UTM+AI 爬虫日志解析)
- WebMCP / agent 任务就绪静态审计
- robots.txt / llms.txt / 9 类 AI 发现文件 / 实体层 JSON-LD schema 生成
- 批量站点审计 + HTML/SARIF 报告 + CI 回归

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

## v1.1 新增:从「诊断+知识」到「诊断 → 产出 → 度量」

**产出层(最强差异化,商业工具把改写锁死在自家黑盒):**

```bash
# 改写指令编译器:吃打分 → 出可喂任意 LLM 的精确改写指令包(按目标引擎分叉)
python3 scripts/geo_cli.py rewrite --input page.html --engine perplexity
# GEO Content Brief 生成器(以可被引用性为骨架,区别于市面 SEO brief)
python3 scripts/geo_cli.py brief --topic "公众号怎么排版" --section "X是什么" --engine 豆包
```

**度量层(成熟 SaaS 命门,我做可解释离线版,采集寄生宿主 agent):**

```bash
# buyer prompt 集生成(意图问句,漏斗×persona,非品牌优先,中英双语)
python3 scripts/geo_cli.py prompts --brand 智能排版器 --category 公众号排版工具 --competitor 壹伴
# Share of Voice 度量(三公式+基准阈值+采样置信度+别名合并)
python3 scripts/geo_cli.py sov --input records.json --brand 智能排版器 --brand-domain x.com
# 「为何没被引用」7 根因诊断
python3 scripts/geo_cli.py diagnose --input page.html
```

**文件+工程层(对标 aeorank 9 文件):**

```bash
python3 scripts/geo_cli.py files --out-dir ./ai-files --site 站名 --url https://x.com   # ai.txt/robots.patch/sitemap/feed/humans.txt
python3 scripts/geo_cli.py schema --type organization --name 公司 --url https://x.com --same-as https://wikidata.org/...
python3 scripts/geo_cli.py report --input page.html --format sarif   # 接 GitHub Code Scanning
python3 scripts/geo_cli.py batch a.html b.html --html report.html    # 批量站点审计
python3 scripts/geo_cli.py attribution --url https://x.com           # GA4 渠道组正则+UTM+日志解析
python3 scripts/geo_cli.py agentready --input page.html              # WebMCP 表单就绪审计
```

**平台发布推荐引擎(v1.2,基于新榜实证信源权重):** 给目标引擎,推荐发哪几个平台权重最高。

```bash
python3 scripts/geo_cli.py recommend --engine 豆包 --engine 元宝   # 想被这俩引用该发哪
python3 scripts/geo_cli.py recommend --engine 豆包 --content-type video
python3 scripts/geo_cli.py recommend --reverse 知乎               # 反向:发知乎能喂哪些 AI
python3 scripts/geo_cli.py recommend --engine cn-all --top 8
```

**全球场景(v1.3):海外 11 引擎(检索地基三套 Bing/Google/独立)+ 20+ 平台权重矩阵 + 中外双轨爬虫归因。**

```bash
python3 scripts/geo_cli.py recommend --engine chatgpt --engine perplexity --content-type b2b   # B2B SaaS 该发哪
python3 scripts/geo_cli.py recommend --engine gemini        # Gemini 几乎不引 Reddit,推 YouTube/LinkedIn
python3 scripts/geo_cli.py recommend --engine overseas-all --top 10
python3 scripts/geo_cli.py attribution --log access.log     # 中外分桶+训练/检索/用户三类+Grok盲区
```

注意:海外引用每月 40-60% 翻盘,recommend 输出的海外数字是方向性;Gemini 几乎不引 Reddit、ChatGPT 命脉是 Wikipedia、Perplexity 押 Reddit+G2,按引擎差异化。

**新增知识库:** `knowledge/05-engine-differences.md`(引擎差异矩阵)、`knowledge/06-ai-visibility-measurement.md`(度量学)、`knowledge/07-global-scenario.md`(海外全球场景)、`03-publishing-channels.md` 补国产引擎信源权重表(新榜 1683.6 万条实证,来源 newrank.cn/report/detail/433)+ 平台依附 vs 域名主权。

---

兼容 Claude Code / Codex / OpenClaw / Hermes,由单源转译。开源协议 MIT。
