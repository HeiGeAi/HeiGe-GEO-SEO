# Changelog

## v1.9.0 (2026-06-28)

把作战手册做成能交付的可视化产物,再加对标作战。

### `playbook --html`:静态可打印 HTML 作战手册

- playbook 从命令行 markdown 升级成静态零脚本可打印的 HTML 作战手册:八层瓶颈定位卡片(按瓶颈层着色)+ 评分条(6 维 / 内容工程 / 证据引用层)+ 统一行动清单(按层着色)+ 信源分层卡片(P0/P1/P2 平台 chip)+ 监测采集。系统字体、`@media print` 适配、品牌名 HTML 转义,可直接甩给客户。

### `compare`:对标作战

- 你的页 vs 竞品页,每页打 6 维 + 内容工程 11 要素,出综合分排名 + 你落后的差距要素(竞品比你高的要素,差距最大优先)+ 一句话裁决。
- 只比内容质量层(可离线);谁真被引用还要跑 measure 采样。差距要素只用真实素材补,绝不编造。

测试 252 → 265。构建四套适配全过,完整性自检全过。

## v1.8.0 (2026-06-28)

从工具箱收口成产品。前面七个版本堆了 27 个能力强但分散的命令,用户面对一排命令不知从哪下手。v1.8 给产品装上正门。

### 新增 `playbook`:旗舰命令,一键出完整 GEO 作战手册

- 一条命令吃 网页 + 品牌 + 品类 + 目标引擎,编排整套工具产出一份整合作战手册:
  1. **八层瓶颈定位(产品的脑子)**:综合 score + cescore + diagnose,判定卡在八层哪一层(内容质量层 / 索引层 / 信源策略层)、第一动作做什么。内容太弱先补内容,内容过关但国内收录有障碍先解决收录,都过关则瓶颈在信源投放。
  2. 现状诊断(6 维 + 内容工程 11 要素 + 为何没被引用根因)。
  3. 信源策略(sourcing)、逐段改写指引(cescore --annotate)、监测采集闭环。
  4. **跨层统一行动清单**:把各工具的发现按 ROI 合并排序(证据引用层 > 收录 > schema/结构 > 信源投放 > 监测)。
- 编排已有 lib,不重造轮子。

### 新增 `measure`:监测采集闭环(八层第 8 层治理/反馈)

- `measure --kit`:出采集工具包,内含采样协议(监测=概率,每问句每平台 5 次、约 5 平台共 25 次取均值)+ buyer prompt 集 + records.json 模板 + 喂回哪些命令。
- `measure --input records.json`:把宿主 agent/人工采集回的 AI 回答,一键同时喂 sov(占位/被推荐概率/声量份额)+ lostprompt(竞品夺走)+ factcheck(错误信息),出综合监测表。
- 度量学离线,采集寄生宿主 agent,刻意不实时联网监控,绝不编造 AI 回答。

测试 233 → 246。构建四套适配全过,完整性自检全过。

## v1.7.0 (2026-06-28)

补齐会议方法论的另一半:v1.6 做了内容质量层(八层机制 5-7),v1.7 做信源策略层(八层机制 2-4),两条腿凑齐才是姚金刚讲的完整 GEO。

### 新增 `sourcing`:信源策略层(八层 2-4 索引/查询/检索)

- 给品类/词根 + 目标引擎,产出:**层 3 查询**词根→问句矩阵(信息/商业/交易三类意图)、**层 2 索引**收录前置动作(国内求收录占平台、海外配 robots)、**层 4 检索**引擎信源偏好诊断 + **P0/P1/P2 分层投放 SOP**(跨引擎共识平台进 P0)。
- **诊断闭环**:监测=概率(25 次取均值)→ `prompts` 扩问句 → `sov` 看占位 → `lostprompt` 看竞品夺走 → 回填迭代信源。
- 复用 `recommend` 已核实的新榜 1683.6 万条实证权重表,不另起炉灶。

### `cescore` 闭环升级

- **`--query` 真需求匹配**:喂目标问句集,语义密度要素从启发式近似(低置信)升级成真实需求覆盖率(高置信),输出 `query_coverage`,有 query 时语义不再被排除出「最该先补」。还掉 v1.6 复审欠的语义低置信债。
- **`--annotate` 段落级要素标注**:逐段标出承载哪些要素、最该补啥(会议的段落拆解技法),把总分变成逐段可落地的改写指引。

### 八层贯通 + 工作流对齐

- 知识库 08 加「八层 → 症状 → 工具路由」表:一个问句没被引用先判断卡在哪层,再用对应工具修(索引→sourcing/baidu-push,查询→sourcing/prompts,检索→sourcing/recommend,重排装配引用→cescore/score,治理→sov/lostprompt)。
- GeoFlow 8 模块工具映射补 sourcing;十阶段工作流 02 调研接 sourcing、03/07 评分接 cescore --query、05 生产接 cescore --annotate、08 分发接 sourcing 分层。

测试 210 → 226。构建四套适配全过,完整性自检 123 项全过。

## v1.6.0 (2026-06-27)

内容工程层:把 WaytoAGI《GEO 内容工程》公开课(姚金刚)的核心方法论落进产品。该方法论来自爬 1 万条 AI 结果的高频引用特征研究 + 自爬国内 AI 平台引用数据实验,给出带公式的要素权重,是市面少见的硬料。

### 新增 `cescore`:内容工程 11 要素加权评分

- 按 11 要素、9 分层给单篇内容打分,每个要素带可计算公式和规则权重,回答「这一篇为什么会(不会)被 AI 反复引用」。
- **证据引用层合计 43%**(权威原文引语 16% + 统计数据 14% + 可引用性 13%),是被引用第一杠杆,输出会优先暴露这层的缺口。
- 补齐 6 维评分卡里 D(可抽取性)偏粗的内容质量维度,`score` 看大盘和基础设施,`cescore` 钻内容质量被引用要素,两者并用。
- 统计数据要素已剔除 ISO 日期/版本号,不把 `2026-06-27` 当统计数字(沿用 number_count 的历史修法)。

### 新增知识库与方法论

- `knowledge/08-content-engineering.md`:八层机制(记忆→索引→查询→检索→重排→装配→引用→治理,理清内容质量层 5-7 vs 信源策略层 2-4)、11 要素加权模型表、GeoFlow 8 模块内容主链路、工程系统思维(系统=目标+要素+关系)、监测=概率(25 次取均值)、跨境与媒介补充。
- `methodology/content-engineering-scorecard.md`:cescore 实现口径、与 6 维卡的分工、诚实边界、改写联动。

### 诚实边界

- 权重是方向性口径(来自单一应用型研究,带主观性),语义类要素无目标 query 时按启发式近似,机器评分不替代人工终审,素材不足绝不编造引语/统计/来源。
- cescore 打的是内容质量(八层机制 5-7 层),被引用还取决于信源策略(2-4 层,发哪个平台/能否被收录),那是 `recommend`/`baidu-push` 的活。

测试 193 → 203。构建四套适配全过,完整性自检 121 项全通过。

## v1.5.0 (2026-06-23)

收官版:把历轮 The Agency 专家审查点过的 backlog 一次性补齐,从"诊断+产出+度量"做到"测质量+管风险+全栈覆盖"。

### 引用质量层(从"测覆盖"到"测质量管风险")

- `sov` 加被引 **sentiment**(正/中/负,防把负面提及误报成可见度)、**earned vs owned 引用拆分**(自有刷引用抗波动差)、**多轮 by_turn**(首轮命中 vs 后续留存,turn 管对话演进 run 管抖动)。
- `factcheck`:品牌错误信息纠正,你提供真相→标 AI 说错的(说你停产/价格错),接实体层修复。
- `lostprompt`:竞品替换分析,找竞品占位你缺席的 prompt,按引擎聚类,标该夺回哪些。
- `score` 加 `multimodal`(图 alt 覆盖/视频转录/VideoObject schema)独立报告。

### agentic 完善

- `agentready` 加 **agent-hostile 反模式检测**(CAPTCHA/file 上传/canvas 控件/placeholder 当 label/强制注册墙,今天就让 Operator/Claude/Gemini 等 computer-use agent 任务失败)+ **imperative WebMCP 扫描**(navigator.modelContext/registerTool);declarative 属性名标注成熟度,诚实提示未定稿。
- schema 加 `potentialAction`(OrderAction/ReserveAction + EntryPoint)、`speakable`、`SoftwareApplication`。

### SEO 深水 + AEO 完善

- `cannibalize`(关键词蚕食:跨页 title/H1/关键词重叠)、`internal-links`(内链/孤儿页审计)、`score` 加 `onpage_serp`(title/meta 长度)、`cwv`(Core Web Vitals 评估,喂 PSI 数值,诚实标 field data 不离线测)、`token`(token 预算近似估算)、`baidu-index-check`(国产搜索收录自查指引)。
- `gen_llms_full`(llms-full.txt 拼接,喂 RAG/IDE/agent)。

新增 lib:factcheck/lostprompt/cannibalize/internal_links/cwv/token_budget。测试 159 → 184 全过。

## v1.4.0 (2026-06-22)

补上轮专家审查点名的两处偏科:SEO 弱于 GEO、国内工具化弱于海外。建完又派三位专家(代码/SEO/百度SEO)复审,修掉复审挖出的问题才发布。

### SEO 偏科补强

- **搜索意图分类器**(`intent` 命令 + `brief --intent`):信息/商业/交易/导航四类 → 内容类型 + schema + GEO/SEO 战术映射。英文用词边界匹配(避免 whichever→which 误判),低置信度提示人工确认。
- **链接权威与 earned media 知识层**(知识库 03):国内外链获取 + 海外 digital PR/资源页/断链/未链提及;诚实标注反链需外部数据不编造。
- **hreflang 国际化生成器**(`hreflang` 命令)。
- 评分卡 D5 加「出站权威引用质量」(按 host 后缀精确匹配,防钓鱼域误判)。

### 国内工具化补强

- **百度主动推送生成器**(`baidu-push` 命令):国内收录第一杠杆,生成可跑 curl;site/token URL 编码、URL 逐行校验防 shell 注入;`--fast` 诚实标注快速收录接口已基本下线;补真实配额坑(10 万/天共享、重复推旧链降配额、协议须一致)。
- **国产搜索引擎覆盖**:cn-index robots 放行神马 YisouSpider / 360Spider,attribution 爬虫日志识别同步,知识库 02 补国产爬虫 UA 对称表(神马按实测标"不遵守 robots")。
- **cn 评分修正**:国内 llms.txt 影响弱、未提供不重罚,且修了"提供烂 llms.txt 反而比不提供分低"的倒挂,消除评分与知识库自相矛盾。
- 知识库 04 补百度收录提交矩阵 + 移动/小程序可见性 + 国内度量(百度搜索资源平台/百度统计对照 GSC/GA4)。

### 定位说明(名实对齐)

这是 GEO 为主、SEO 聚焦"on-page 可被引用性 + 国内收录 + 国际化"的工具。完整 SEO 的关键词研究、外链反查、Core Web Vitals 实测、内链/cannibalization 审计需外部数据或属下阶段,当前不覆盖,README 已写明不当全功能 SEO 套件。

测试 138 → 159 全过。

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
