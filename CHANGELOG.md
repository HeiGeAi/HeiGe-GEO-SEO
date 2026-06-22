# Changelog

## v1.3.1 (2026-06-22)

The Agency 六位专家(GEO引用策略/AEO基础/SEO/百度SEO/agentic搜索/代码审查)并行审查后的修正版。

### 修真 bug(专家挖出、已复现)

- `number_count` 把日期 `2025-06-22`、版本号 `1.2.3` 当成统计数字,导致评分卡 D5「内容可抽取性」虚高。修正:计数前剔除 ISO 日期和版本号。
- `_domain` 用 `lstrip("www.")` 实为字符集剥离,把 `webflow.com` 削成 `ebflow.com`,污染 SoV 引用归属。修正:只剥 `www.` 前缀。
- 删两处死代码(`diagnose.has_answer` 自相矛盾、`reverse` 子串过宽导致 `reverse("网")` 命中全部引擎)。
- 补 19 个边界与回归测试(空 HTML、畸形标签、空 records、日期误判、域名前缀、短查询、未知引擎),堵住"happy path 裸奔"。

### 补 AEO 承诺但没实现的 schema(修文档与代码的一致性裂缝)

知识库 04 标了「必上/建议上」却没实现的 schema,现已补到 `generators.py` 并接入 CLI:

- `gen_breadcrumb`(BreadcrumbList)、`gen_itemlist`(ItemList,命中"最好的 X")、`gen_review`(Review)
- `gen_graph`(用 `@graph` + `@id` 把多个 schema 串成可信链,落实知识库 04 第2节核心原则)
- `instruction` 引擎分叉表补齐 grok/copilot/通义(与 platform_recommend 对齐)

测试 119 → 138 全过。

## v1.3.0 (2026-06-21)

### 全球场景补全(把"中国优先,海外作对照"补成真正全球级)

基于对海外 GEO 场景的 4 路深研(引擎全景 / 平台引用权重 / 爬虫归因 / 发布 SOP,全部带源)。

- **海外引擎从大四扩到 11 个**(`recommend`):加 Copilot、Grok、Meta AI、You.com、Brave、Mistral、DuckDuckGo。核心洞察是检索地基只有三套(Bing 系 ChatGPT/Copilot/Meta/DDG、Google 系 Gemini、独立索引 Brave→Mistral),Copilot/Brave/Mistral 是经典 SEO 可打的蓝海。
- **海外平台从 6 个扩到 20+ 并按引擎差异化加权**:Gemini 几乎不引 Reddit(0.1%)、ChatGPT 命脉是 Wikipedia、Perplexity 押 Reddit+G2、B2B 押 LinkedIn/G2/Capterra。新增 b2b / b2c 内容类型分流。
- **attribution 中外双轨升级**:爬虫日志区分国内 vs 海外引擎、分训练/检索/用户触发三类、标 Grok/Bytespider/Copilot-agent 等 UA 盲区;GA4 渠道组正则扩到含全部国内外引擎域名;反向查平台带中外地区标签。
- **新增知识库 `07-global-scenario.md`**:海外 11 引擎表 + 平台权重矩阵 + 逐平台发布 SOP(Reddit 90/10/养号、Wikipedia notability、YouTube 字幕、LinkedIn 双押、G2 准入门、技术内容)+ B2B/B2C 分流 + 多语言。

### 诚实红线(写进知识库与 recommend 输出)

海外引用每月 40-60% 翻盘、半年 70-90% 换新,所有百分比标方向性;口径分总量% vs Top10 share;单域名极少超总引用 5%;别押单平台,4+ 平台一致覆盖抗波动约 70 倍,82-94% 引用来自 earned media;一级证据(GEO 论文)与厂商数字分级。

测试 106 → 119 全过。

## v1.2.0 (2026-06-21)

### 平台发布推荐引擎(`recommend`)

把已核实的国产引擎信源权重表从静态知识变成会推荐的引擎。

- **正向**:给目标引擎(可多选,或 cn-all / overseas-all)+ 可选内容类型,推荐发布在哪几个平台权重最高,按加权分排序,每条标来源。`recommend --engine 豆包 --engine 元宝` 会把同时喂两个引擎的平台(如搜狐)排前面。
- **反向**:`recommend --reverse 知乎` 查某平台能喂哪些 AI 引擎。
- **内容类型适配**:video / tech / 种草 / 消费,追加对应平台并加权(如视频内容把抖音/B站/YouTube 提权)。

### 数据源核实与归因修正

- 核实新榜《超 1600 万条 AI 引用数据,解密GEO站点偏好》报告真实(来源 newrank.cn/report/detail/433):约 1683.6 万信源、142.9 万次问答、2025 年 12 月、四大平台(豆包/元宝/DeepSeek/Kimi)。豆包→字节系、元宝→公众号 10%、DeepSeek→搜狐/百度百科/网易、Kimi→公众号/搜狐 全部核对一致。
- **归因修正**:新榜这份报告的四大平台不含文心,信源权重表里文心一行标注为"百度生态通识(非新榜)"。知乎 35.3% 来自量子位智库(非新榜),原归因正确。

测试 96 → 106 全过。

## v1.1.0 (2026-06-21)

把工具从「诊断 + 知识」升级成「诊断 → 产出 → 度量」全链路,同时焊死中国优先护城河。基于对 20+ 成熟 GEO 产品的竞品深研(商业可见度监控 SaaS Profound/Otterly/Peec/Brandlight/Scrunch 等、内容优化工具 Surfer/Jasper/Writesonic/AutoGEO、技术审计 aeorank/geo-optimizer、国内透镜GEO/GEOBase 等)。

### 产出层(最强差异化)

- **改写指令编译器**(`rewrite`):吃打分结果,输出可喂任意 LLM 的精确改写指令包。每条含 GEO 方法、预期提升、精确改写指令、按目标引擎分叉、反 AI 味约束。LLM 无关,绕开商业工具把改写锁死在自家黑盒的封闭性。
- **GEO Content Brief 生成器**(`brief`):以可被引用性为骨架,区别于市面 SEO brief。
- **反 AI 味约束库**(`anti_ai`):把人机感做成显式约束子句,复用 HeiGe 写作硬规则,也能当检测器。

### 度量层(可解释离线版)

- **buyer prompt 集生成器**(`prompts`):意图问句,漏斗 × persona × 品牌/非品牌,非品牌优先,中英双语。
- **Share of Voice 度量**(`sov`):三公式(Mention/调和加权/Citation)+ 竞争位基准阈值 + 采样置信度 + 别名合并。
- **「为何没被引用」7 根因诊断**(`diagnose`):确定性清单,每条 pass/fail + 修复动作,含国内 ICP 备案检测。
- **GEO 归因检测**(`attribution`):GA4 渠道组正则(含国内引擎)+ UTM 规范 + 服务器日志 AI 爬虫 UA 解析。

### 文件 + 工程层

- **实体层 schema**:新增 Organization / Person / WebSite,强制 @id + sameAs(AI 引用前置门槛)。
- **9 文件家族**:补 ai.txt、robots.patch、sitemap.xml、answers.json、citations.json、humans.txt、feed.xml。
- **报告**:HTML 自包含报告 + SARIF(接 GitHub Code Scanning)。
- **批量站点审计**(`batch`):弱页优先排序。
- **WebMCP 就绪审计**(`agentready`):表单 agent 可调用性静态审计。

### 知识库增量

- 新增 `05-engine-differences.md`:引擎差异矩阵(各引擎检索机制 + 格式偏好 + 差异化战术)。
- 新增 `06-ai-visibility-measurement.md`:SoV 度量学 + prompt 测试方法 + 归因。
- `03-publishing-channels.md`:补国产引擎信源权重表(新榜 1683.6 万条实证)+ 平台依附 vs 域名主权 + 国产平台发布 SOP。

### 边界(刻意不做)

实时 AI 可见度监控(需常驻爬 9 引擎,违背零依赖)、自动内容改写引擎(交宿主 agent)、训练模型。度量学进 v1.1,采集寄生宿主 agent,联网监控留后续版本。

### 测试

44 → 96 个单测全过,build/validate/案例全绿。

## v1.0.0 (2026-06-20)

首个版本。中国优先的 GEO + SEO 优化系统:四大知识库 + GEO 论文 9 方法与 6 维 22 项评分卡 + 零依赖脚本(打分器/robots/llms.txt/schema)+ 10 阶段工作流 + 单源转译 CC/Codex/OpenClaw/Hermes + 3 案例 + 44 单测 + CI。
