# 方法论 · GEO 可被引用度评分卡

> 这是 HeiGe-GEO-SEO 给内容和页面打分的统一标准,综合四个开源审计项目(geo-optimizer-skill、geo-analyzer、aeorank、aeo-audit)的检测信号交叉验证而成。6 个维度、22 个检查项、满分 100。脚本 `geo_score.py` 按这张卡实现。

---

## 设计判断

**接入信号(爬虫准入 + AI 发现文件)是被引用的前置门票,内容信号(主张密度 + 答案前置 + 结构)才是真正的差异化引擎。** 门票缺了后面全白搭,但只有门票没有好内容也进不了引用池。两者都要,权重分开配。

评分用确定性模式:`score = Σ(check 得分 × 权重)`,同输入同输出,取整 floor 截断,保证可复现。维度 A/B/C/E/F 大多是布尔/正则检查(抓 robots.txt、HEAD 文件、解析 JSON-LD、数标签),无需大模型;维度 D 的语义信号用启发式近似或挂 LLM 抽取。

---

## 维度 A · AI 爬虫准入(18 分)

门票。缺了后面全白搭。

| 检查 | 判定标准 | 权重 |
|---|---|---|
| GPTBot/OAI-SearchBot 准入 | robots.txt 未 Disallow(或显式 Allow)OpenAI 检索类 | 5 |
| ClaudeBot/Claude-SearchBot 准入 | 同上,Anthropic 检索类 | 5 |
| PerplexityBot 准入 | 同上 | 4 |
| 无 CDN/WAF 层拦截 | Cloudflare/Akamai 未额外封 AI UA | 4 |

国内站此维度改判:不屏蔽 `Baiduspider`/`Sogou web spider`/`bingbot`,因为国产 AI 靠这三大索引,详见 [[../knowledge/02-crawler-logic]]。

---

## 维度 B · AI 发现文件(16 分)

| 检查 | 判定标准 | 权重 |
|---|---|---|
| llms.txt 存在且结构合格 | 有文件 + H1 + 分节 + 链接列表 | 8 |
| llms-full.txt / Markdown 端点 | 配套全文版存在 | 3 |
| ai.txt / .well-known | ai.txt 或 ai/*.json 任一存在 | 2 |
| sitemap + RSS 新鲜度 | sitemap.xml 存在且含 lastmod;有 feed | 3 |

诚实提示:llms.txt 当前实证效果弱,这里给分是因为成本低、四家审计都查,不代表它是强排名因子。详见 [[../knowledge/04-webpage-architecture]] 第 7 节。

---

## 维度 C · 结构化数据 Schema(16 分)

FAQPage 单独高配(实测 2.7 倍引用率)。

| 检查 | 判定标准 | 权重 |
|---|---|---|
| FAQPage schema | 存在且 Q&A 配对完整 | 6 |
| 核心 schema 覆盖 | WebSite/Organization/Article 至少 2 类 | 4 |
| Schema 丰富度 | 关键 schema ≥5 个属性 | 3 |
| Schema 有效性 | JSON-LD 可解析、无重复 @type、无语法错 | 3 |

---

## 维度 D · 内容可抽取性(22 分)

被引用的真正发动机,权重最高。

| 检查 | 判定标准 | 权重 |
|---|---|---|
| 主张密度 claim density | ≥4 条可抽取事实/100 词 | 6 |
| 答案前置 answer-first | 首个主张/直接答案落在前 100 词 | 5 |
| 句长 sentence structure | 平均 15~20 词/句 | 3 |
| 信息密度/篇幅 | 正文落在 800~1500 词区间(过长扣分) | 4 |
| 统计数据 + 外部引用 | 含具体数字/百分比 + 带外链来源 | 4 |

信息密度实测依据:<1000 词页约 61% 被 AI 覆盖,>3000 词页骤降到约 13%。短而密的内容抽取率更高。

---

## 维度 E · 内容结构与可解析性(16 分)

| 检查 | 判定标准 | 权重 |
|---|---|---|
| 标题层级 | 单一 H1 + 合理 H2/H3 嵌套 | 4 |
| 列表与表格 | 含 ≥1 个 list 或 table | 3 |
| 定义块/Q&A 标题 | 有"What is/How to"式标题或 dl/details | 3 |
| 语义三元组密度 | 句子多为清晰主-谓-宾结构 | 3 |
| 无反引用信号 | 无 CTA 过载/弹窗/关键词堆砌/付费墙/薄内容 | 3 |

---

## 维度 F · 信任、实体与权威(12 分)

| 检查 | 判定标准 | 权重 |
|---|---|---|
| 作者署名 + Person schema | 有具名作者 + author/Person 标记 | 3 |
| 知识图谱外链 | sameAs 指向 Wikipedia/Wikidata/LinkedIn/Crunchbase | 3 |
| 实体一致性 + 命名实体密度 | 品牌名跨页一致、专有名词充足 | 3 |
| 内容新鲜度 | dateModified 近期 + 版权年份当年 | 3 |

---

## 总分与档位

满分 100,分两个合成分供分别看:

- **GEO Score**(被 AI 引用的就绪度)= 维度 A + B + C + D 的得分占比
- **SEO Score**(被搜索引擎排名的就绪度)= 维度 C + E + F + 技术地基的得分占比

档位:

| 分数 | 档位 | 含义 |
|---|---|---|
| 85~100 | 优 | 已就绪 |
| 70~84 | 良 | CI 通过门槛 |
| 40~69 | 待优化 | 有硬伤 |
| 0~39 | 危急 | 基本不可见 |

---

## 否决项(Veto,一票封顶)

借鉴 CORE-EEAT 的否决机制,以下任一失败,总分直接封顶 60,不让高分掩盖致命问题:

- **维度 A 全部 AI 检索爬虫被屏蔽**(技术上不可被引)
- **正文纯 CSR 渲染,curl 看不到内容**(爬虫拿不到)
- **schema 造假**(标了 FAQPage 没问答,会被判作弊反噬)

---

## CORE-EEAT 与 CITE 双框架(内容门与域门,进阶审计)

脚本的 6 维评分卡负责自动化打分,人工深度审稿时再叠这套定性框架(来自 seo-geo-claude-skills):

**内容门 CORE-EEAT(80 项,8 维 × 10):**

- GEO 轴 CORE:**C** Contextual Clarity 语境清晰 / **O** Organization 结构组织 / **R** Referenceability 可引用性 / **E** Exclusivity 独占性 → GEO Score = (C+O+R+E)/4
- SEO 轴 EEAT:**E** Experience 经验 / **E** Expertise 专业 / **A** Authority 权威 / **T** Trust 可信 → SEO Score 同理

**域门 CITE(40 项,4 维 × 10):**

- **C** Citation 被引用情况 / **I** Identity 身份可识别 / **T** Trust 信任(HTTPS+编辑政策+评论真实) / **E** Eminence 声誉显赫度

三态裁决:SHIP(无致命问题)/ FIX(有问题但不致命)/ BLOCK(2+ 否决项或致命信任问题)。BLOCK 是不可绕过的人工 checkpoint,详见 [[../workflow/stages]]。

一处纠偏:网上常把 CORE 错写成 Credibility/Originality/Relevance/Expertise,以 SKILL.md 原文为准,CORE = Contextual Clarity / Organization / Referenceability / Exclusivity。

---

## 相关

- 提分用哪些改写方法 → [[geo-methods]]
- 评分的技术信号怎么落地 → [[../knowledge/04-webpage-architecture]]
- 脚本实现 → `geo_score.py`
