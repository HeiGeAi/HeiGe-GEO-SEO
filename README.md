# HeiGe-GEO-SEO

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Agents](https://img.shields.io/badge/Agents-Claude%20Code%20·%20Codex%20·%20OpenClaw%20·%20Hermes-blue)
![Market](https://img.shields.io/badge/Market-China%20First-red)
![Python](https://img.shields.io/badge/Python-stdlib%20only-yellow)
![Tests](https://img.shields.io/badge/tests-226%20passing-brightgreen)

> 中国市场优先的 GEO(生成式引擎优化)+ SEO 内容优化系统。让你的内容和网页被豆包、通义千问、DeepSeek、文心、腾讯元宝、ChatGPT、Perplexity、Claude、Gemini 抓取并引用。
>
> China-first Generative Engine Optimization (GEO) + SEO toolkit. Make your content get cited by Doubao, Qwen, DeepSeek, ERNIE, Tencent Yuanbao, ChatGPT, Perplexity, Claude and Gemini.

中文 | [English below](#english)

---

## 为什么做这个

市面上的 GEO 开源工具几乎全盯着 ChatGPT 和 Perplexity,**没有一个认真做中国大模型的抓取和发布逻辑**。可豆包月活 3.45 亿是全国第 1,通义千问 1.66 亿第 2,这套用户优化工具不能不懂中国。

HeiGe-GEO-SEO 把三层缝成一个原创工具:

- **学术方法论** 来自 GEO(KDD 2024)和 AutoGEO(ICLR 2026)两篇论文,9 种改写方法的真实提升幅度、按排名分流的逻辑、GEU 合规护栏。
- **工程化框架** 综合 4 个头部开源审计项目,提炼出 6 维 22 项的可被引用度评分卡。
- **中国市场抓取逻辑** 原创差异点:国内 AI 没公开爬虫、靠博查/搜狗/百度索引和自家生态,GEO 是求收录加占平台,robots.txt 基本失效。

## 一句话核心判断

**国内 GEO 是求收录加占平台的游戏,海外 GEO 是配 robots.txt 的游戏。** 两套打法别混用。

## 能做什么

| 你的需求 | 工具给你 |
|---|---|
| 判断给哪个 AI 优化 | 大模型分类库(9 大模型 DAU + 引用行为) |
| 搞清 AI 怎么抓到内容 | 抓取逻辑库(国内三条路径 + 海外真实爬虫 UA) |
| 内容发哪曝光 | 发布渠道库(一稿四态 + 国内押生态海外押 Reddit) |
| 网页怎么建 | 网页架构库(语义 HTML + schema + SSR 生死线 + 国内 ICP) |
| 改写提升被引用率 | GEO 方法库(加引语+41%、按排名分流、合规红线) |
| 给内容打分 | 评分卡脚本(6 维 22 项,确定性,可进 CI) |
| 生成配置文件 | robots.txt / llms.txt / JSON-LD schema 一键生成 |

## v1.1 新增:诊断 → 产出 → 度量

v1.0 是「诊断 + 知识」,v1.1 补上「产出」和「度量」两层,全部零依赖可离线,采集寄生宿主 agent。

**产出层(最强差异化,商业工具把改写锁死在自家黑盒,我做 LLM 无关的指令编译器):**

```bash
# 改写指令编译器:吃打分 → 出可喂任意 LLM 的精确改写指令包(按目标引擎分叉 + 反 AI 味约束)
python3 scripts/geo_cli.py rewrite --input page.html --engine perplexity
# GEO Content Brief 生成器(以可被引用性为骨架)
python3 scripts/geo_cli.py brief --topic "公众号怎么排版" --section "X是什么" --engine 豆包
```

**度量层(成熟监控 SaaS 的命门,我做可解释离线版):**

```bash
python3 scripts/geo_cli.py prompts --brand 智能排版器 --category 公众号排版工具 --competitor 壹伴
python3 scripts/geo_cli.py sov --input records.json --brand 智能排版器 --brand-domain x.com
python3 scripts/geo_cli.py diagnose --input page.html   # 为何没被引用,7 根因
```

**文件 + 工程层(对标 aeorank 9 文件):**

```bash
python3 scripts/geo_cli.py files --out-dir ./out --site 站名 --url https://x.com  # ai.txt/robots.patch/sitemap/feed/humans.txt
python3 scripts/geo_cli.py schema --type organization --name 公司 --same-as https://wikidata.org/...
python3 scripts/geo_cli.py report --input page.html --format sarif   # 接 GitHub Code Scanning
python3 scripts/geo_cli.py batch a.html b.html --html report.html    # 批量审计
python3 scripts/geo_cli.py attribution --url https://x.com           # GA4 渠道组正则 + UTM + 日志解析
python3 scripts/geo_cli.py agentready --input page.html              # WebMCP 就绪审计
```

**v1.7 信源策略层:补齐会议方法论的另一半(八层机制 2-4 索引/查询/检索)。v1.6 做内容质量,v1.7 做信源策略,两条腿凑齐才是完整 GEO。**

```bash
# 信源策略规划:词根→问句矩阵 + 引擎信源偏好诊断 + P0/P1/P2 分层投放 + 诊断闭环
python3 scripts/geo_cli.py sourcing --category 公众号排版工具 --root 公众号排版 --engine 豆包 --engine 元宝
# cescore 闭环:--query 真需求匹配(语义去低置信)、--annotate 段落级要素标注
python3 scripts/geo_cli.py cescore --input page.html --query "公众号排版工具哪个好"
python3 scripts/geo_cli.py cescore --input page.html --annotate
```

- **八层 → 症状 → 工具路由**:一个问句没被引用,先判断卡在哪层(索引没收录 / 查询没匹配 / 检索没召回 / 内容没被选中 / 想看反馈),再用对应工具修,别上来就改内容或盲发。
- `sourcing`(信源策略,2-4 层)和 `cescore`(内容质量,5-7 层)是两条腿,缺一条 GEO 都不完整。

**v1.6 内容工程层:把 WaytoAGI《GEO 内容工程》公开课(姚金刚)的核心方法论落进产品。**

```bash
# 内容工程 11 要素加权评分:回答「这一篇为什么会(不会)被 AI 反复引用」
python3 scripts/geo_cli.py cescore --input page.html
```

- 11 要素、9 分层,每个带可计算公式和规则权重。**证据引用层合计 43%**(权威原文引语 16% + 统计数据 14% + 可引用性 13%)是被引用第一杠杆,输出优先暴露这层缺口。
- 补齐 6 维卡里 D(可抽取性)偏粗的内容质量维度:`score` 看大盘和基础设施,`cescore` 钻被引用要素,两者并用。
- 新知识库 `08-content-engineering.md`:八层机制(记忆→索引→查询→检索→重排→装配→引用→治理,内容质量打 5-7 层,信源策略打 2-4 层)+ GeoFlow 8 模块 + 系统=目标+要素+关系 + 监测=概率(25 次取均值)。
- 诚实边界:权重是方向性口径(来自单一研究),语义类要素无 query 时启发式近似,机器评分不替代人工终审,素材不足绝不编造引语/统计/来源。

**v1.5 收官:把历轮专家点过的 backlog 一次性补齐。**

- **引用质量层**:`sov` 现含被引 sentiment、earned/owned 引用拆分、多轮留存;`factcheck`(品牌错误信息纠正)、`lostprompt`(竞品替换分析);`score` 加多模态(图 alt/视频转录)。从"测被不被引"升到"测引用质量 + 管被引风险"。
- **agentic 完善**:`agentready` 加 agent-hostile 反模式检测(CAPTCHA/file/注册墙,今天就让 computer-use agent 任务失败)+ imperative WebMCP 扫描;schema 加 `potentialAction`/`speakable`/`SoftwareApplication`。
- **SEO 深水**:`cannibalize`(关键词蚕食)、`internal-links`(内链/孤儿页)、`onpage_serp`(title/meta)、`cwv`(Core Web Vitals 评估)、`token`(预算估算)、`baidu-index-check`(收录自查)。

**v1.4 补 SEO 偏科 + 国内工具化(The Agency 专家组审查后):**

```bash
python3 scripts/geo_cli.py intent --query "最好的公众号排版工具对比"   # 搜索意图分类→内容类型+schema+战术
python3 scripts/geo_cli.py brief --topic "公众号排版" --intent "公众号怎么快速排版"
python3 scripts/geo_cli.py baidu-push --site xsbbai.com --token T --url https://xsbbai.com/a   # 百度主动推送(国内收录第一杠杆)
python3 scripts/geo_cli.py hreflang --locale "zh-CN::https://x.com/" --locale "en::https://x.com/en/"
```

SEO 侧补了搜索意图分类链 + 外链/earned media 知识层 + hreflang + D5 出站引用质量;国内侧补了百度主动推送、神马/360 爬虫覆盖、cn 评分修正(国内 llms.txt 不再错罚)、国产爬虫 UA 对称表。

**定位说明(名实对齐):这是 GEO 为主、SEO 覆盖到 on-page 可被引用性 + 国内收录 + 国际化 + 站点级审计的工具。** v1.5 已补 Core Web Vitals 评估(喂 PSI 数值,field data 不离线测)、内链/孤儿页审计、关键词蚕食检测(title/关键词静态启发式,非 GSC 驱动,会漏意图重合型,完整版需 GSC 数据)。仍需外部数据的部分:关键词搜索量/难度、反链(backlink)反查,工具不内置抓取、不编造,缺数据标 unknown。不当全功能 SEO 套件(如 Ahrefs/Semrush)用。

**平台发布推荐引擎(v1.2,基于新榜 1683.6 万条实证):** 把信源权重表从静态知识变成会推荐的引擎,给目标引擎推荐发哪几个平台权重最高。

```bash
python3 scripts/geo_cli.py recommend --engine 豆包 --engine 元宝   # 想被这俩引用该发哪(权重排序+来源)
python3 scripts/geo_cli.py recommend --reverse 知乎               # 反向:发知乎能喂哪些 AI
python3 scripts/geo_cli.py recommend --engine cn-all --top 8      # 国内全引擎
```

**全球场景(v1.3):把海外那半边补齐成全球级。** 海外引擎从大四扩到 11 个(检索地基只有三套:Bing 系 ChatGPT/Copilot/Meta/DDG、Google 系 Gemini、独立索引 Brave→Mistral),平台权重按引擎差异化(Gemini 几乎不引 Reddit、ChatGPT 命脉是 Wikipedia、Perplexity 押 Reddit+G2),attribution 区分中外引擎爬虫并标 Grok 等 UA 盲区。

```bash
python3 scripts/geo_cli.py recommend --engine chatgpt --engine perplexity --content-type b2b
python3 scripts/geo_cli.py recommend --engine overseas-all --top 10
python3 scripts/geo_cli.py attribution --log access.log   # 中外分桶+训练/检索/用户三类
```

**知识库增量:** 引擎差异矩阵(05)、AI 可见度度量学(06)、海外全球场景(07)、国产引擎信源权重表(新榜 1683.6 万条实证,[来源](https://www.newrank.cn/report/detail/433))+ 平台依附 vs 域名主权。完整升级背景见 [CHANGELOG.md](CHANGELOG.md)。

## 快速开始

零依赖,只要 Python 3。

```bash
# 给一个网页打 GEO 可被引用度分(6 维 22 项)
python3 scripts/geo_cli.py score --input page.html

# 生成 AI 爬虫 robots.txt(只曝光不喂训练)
python3 scripts/geo_cli.py robots --strategy expose-only --sitemap https://example.com/sitemap.xml

# 生成 JSON-LD 结构化数据
python3 scripts/geo_cli.py schema --type article --title "标题" --author "黑哥" --org "黑哥AI"

# 生成 FAQPage(实测带来 2.7 倍引用率)
python3 scripts/geo_cli.py schema --type faqpage --qa "GEO 是什么::优化内容被 AI 引擎引用的实践"

# 生成 llms.txt
python3 scripts/geo_cli.py llms --site "黑哥AI" --summary "AI 落地实战" --links links.txt
```

## 跑通案例

```bash
cd cases && python3 run_cases.py
```

三个真实案例(出海 SaaS 落地页、国内公众号深度文、国内产品页)的端到端优化结果:

| 案例 | 优化前 | 优化后 | 提升 |
|---|---|---|---|
| 出海 SaaS 落地页 | 15 (危急) | 48 (待优化) | +33 |
| 国内公众号深度文 | 43 (待优化) | 67 (待优化) | +24 |
| 国内产品页 | 41 (待优化) | 62 (待优化) | +21 |

每个案例的 output/ 里有基线评分、生成的 robots/schema/llms、注入后复评和发布建议。

## 兼容所有 AI Agent 工具

一份 canonical 单源(`source/`)零依赖转译成四套自包含适配包:

```bash
python3 build.py
```

| 运行时 | 入口 | 安装 |
|---|---|---|
| Claude Code | `SKILL.md` | 放进 `~/.claude/skills/` 自动触发 |
| Codex | `AGENTS.md` | 放进 skills/ 或项目根引用 |
| OpenClaw | `SKILL.md` + `openclaw.json` | 放进技能目录 |
| Hermes | `skill.md` | 加载为技能定义 |

产物在 `adapters/<runtime>/heige-geo-seo/`,每套都含完整知识库和脚本,可独立分发。

## 项目结构

```
source/                 # canonical 单源(唯一真相)
  SKILL.md              # 主技能定义(中英双触发)
  manifest.json         # 元数据,驱动转译
  knowledge/            # 四大知识库
    01-llm-landscape.md       大模型分类
    02-crawler-logic.md       抓取逻辑(中国优先)
    03-publishing-channels.md 发布曝光
    04-webpage-architecture.md 网页架构
  methodology/
    geo-methods.md      # GEO 9 方法 + 排名分流 + 合规红线
    scoring-card.md     # 6 维 22 项评分卡
  workflow/stages.md    # 十阶段工作流 + 2 人工 checkpoint
  templates/            # 四个交付模板
scripts/                # 零依赖 Python 工具(打分器 + 生成器 + CLI)
adapters/               # 转译产物(build.py 生成)
cases/                  # 案例集 + 跑全流程驱动
tests/                  # 44 个单元测试
build.py / validate.py  # 构建链 + 完整性自检
```

## 诚实边界

- **不编造引语、统计、引用。** 素材不足就让你补,GEU 护栏防止改写沦为投毒。Keyword Stuffing 永久禁用(它是负效果)。
- **不把 llms.txt 当排名杠杆。** 实测 97% 的 llms.txt 收到零请求,它是 B2A 基础设施,营销站做了基本无效,开发者工具才值得做。
- **数字是方向参数不是永恒真理。** 各平台引用占比随厂商授权和算法变,工具内标了来源和时间,用前自己校准。
- **人不可被绕过。** Brief 的专家洞察槽位和质量门的 BLOCK 裁决两个 checkpoint 不能自动跳过。GEO 惩罚没有真实洞察的水文。

## 方法论来源

- GEO 论文(KDD 2024)<https://arxiv.org/abs/2311.09735> · 源码 <https://github.com/GEO-optim/GEO>
- AutoGEO(ICLR 2026)<https://arxiv.org/abs/2510.11438> · 仓库 <https://github.com/cxcscmu/AutoGEO>
- 工程框架参考 seo-geo-claude-skills、geo-optimizer-skill、geo-analyzer、aeorank、recomby-geo
- 中国市场数据 QuestMobile 2026 Q1、量子位智库、白杨 SEO 等(详见各知识库末尾来源)

## 许可

MIT License。出品 HeiGeAi(黑哥AI)。

---

<a name="english"></a>

## English

**HeiGe-GEO-SEO** is a China-first GEO (Generative Engine Optimization) + SEO toolkit. Existing open-source GEO tools focus almost entirely on ChatGPT and Perplexity. None take Chinese LLMs seriously, yet Doubao (345M MAU) and Qwen (166M MAU) lead the Chinese market. This tool fuses three layers:

- **Academic methodology** from the GEO (KDD 2024) and AutoGEO (ICLR 2026) papers: 9 rewrite methods with real uplift numbers, rank-based routing, and a GEU compliance guardrail.
- **Engineering frameworks** distilled from 4 leading open-source audit projects into a 6-dimension / 22-check citability score card.
- **China crawler logic** (the original edge): Chinese AIs have no public crawlers and rely on third-party search APIs (Bocha/Sogou/Baidu) and their own ecosystems. In China, GEO is about getting indexed and occupying platforms, not configuring robots.txt.

**Core judgment: China GEO is a get-indexed-and-occupy-platforms game; overseas GEO is a configure-robots.txt game.** Don't mix the two.

### Quick start (zero dependencies, Python 3 only)

```bash
python3 scripts/geo_cli.py score  --input page.html
python3 scripts/geo_cli.py robots --strategy expose-only
python3 scripts/geo_cli.py schema --type faqpage --qa "What is GEO::Optimizing content to be cited by AI engines"
python3 scripts/geo_cli.py llms   --site "Acme" --summary "..." --links links.txt
```

### Compatible with all AI agent runtimes

One canonical source (`source/`) transpiles to self-contained packages for Claude Code, Codex, OpenClaw and Hermes via `python3 build.py`.

### Honest boundaries

No fabricated quotes/stats/citations (GEU guardrail). llms.txt is treated as B2A infrastructure, not a ranking lever. Two human checkpoints cannot be bypassed. Citation-share numbers are calibration parameters, not eternal truths.

MIT License. Built by HeiGeAi.
