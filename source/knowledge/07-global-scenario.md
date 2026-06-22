# 知识库 07 · 海外全球场景

> v1.3 新增。工具原来是"中国优先,海外作对照",这一篇把海外那半边补齐成真正全球级。给 `recommend` 海外引擎和平台、`attribution` 中外分桶、海外发布 SOP 提供依据。

数据核查 2026-06。**先读这条诚实红线再用任何数字。**

---

## 诚实红线(最高优先级)

**海外引用生态每月 40-60% 翻盘,半年 70-90% 换新。所有百分比都是方向性,不是定值,引用时标口径和来源年月。**

四条必须内置的判断:

1. **口径分两套别混:** 总量占比(占全部引用的比例)vs Top10 内份额(在该引擎最常引的前 10 源里的相对份额)。同一个 Reddit,前者约 6%,后者 Perplexity 高到 46.7%,分母不同。
2. **单域名极少超过总引用 5%:** Evertune 2 亿 prompt 研究的反向证据。"Reddit 40%"是出现频率不是引用占比,别理解成赢家通吃。
3. **引擎间源池低重叠:** ChatGPT 和 Perplexity 引用域只重叠 11%。**必须按引擎差异化,别一张表打天下。**
4. **一级证据 vs 厂商数字:** 最硬的独立证据只有 Princeton/Georgia Tech 的 GEO 论文和 2025-09 arXiv 多语言论文。Profound/Semrush/Ahrefs 等厂商博客数字标"方向性"。

---

## 一、海外引擎扩充(大四 → 11 个)

**关键洞察:海外检索地基只有三套。打通其中两套就覆盖大半。**

| 检索后端 | 哪些引擎共用 | 打法 |
|---|---|---|
| **Bing 索引** | ChatGPT、Copilot、Meta AI、DuckDuckGo | 做扎实 Bing SEO(IndexNow/Webmaster Tools)就一次喂四家 |
| **Google 自有索引** | Gemini、AI Overviews、AI Mode | 冲进 Google 前 10 + YouTube |
| **独立索引** | Brave(自建 30B+ 页)、Mistral(走 Brave API) | 单独被 Brave 收录 = 同时打 Brave + Mistral |
| 自有混合 | ChatGPT、Perplexity、Grok | 各有自建检索 + 实时抓取 |

| 引擎 | 检索后端 | 信源偏好 | 该怎么打 |
|---|---|---|---|
| **ChatGPT** | 自有 + Bing 供给 | Wikipedia 命脉 + Reddit + LinkedIn(黑马)+ Forbes | 攻 Wikipedia 词条 + Reddit 真实讨论 + LinkedIn |
| **Gemini/AIO** | Google 自有 | YouTube 命脉 + LinkedIn + Quora;**几乎不引 Reddit(0.1%)** | 押 YouTube 带字幕 + 冲 Google 前 10 |
| **Claude** | 实时 + 走 Brave | LinkedIn 长文 + 传统媒体 + 官方文档 + GitHub | 加局限性段 + 去营销腔 + 结构化文档 |
| **Perplexity** | 自建 + 实时 | Reddit 最重 + LinkedIn + G2 + NIH 学术 | B2B 押 Reddit+LinkedIn+G2,引用密度最高引擎 |
| **Copilot** | Bing 索引 | Bing 已排名页 + Microsoft Learn + Stack Overflow | **蓝海**:扎实 Bing SEO + FAQ/结构化就挤进去 |
| **Grok** | 自有 + 实时 X | **X(Twitter)唯一独家信源** + Reddit | 铺 X 高互动帖;⚠️引用幻觉率历史最高,别当权威 |
| **Meta AI** | Bing + 社交信号 | 消费内容 + Meta 平台社交互动 | 攻 Bing + IG/FB 高互动;引流价值低 |
| **Brave** | 完全独立索引 | 自有索引,每次新鲜召回 | **蓝海**:别只盯 Google/Bing,单独被 Brave 收录 |
| **Mistral** | 走 Brave API | 欧洲/法语源 + 新闻走 AFP+AP | 欧洲必打,优化 Brave 即覆盖 |
| **DuckDuckGo** | Bing + Wikipedia | DuckAssist 重度 Wikipedia | 复用 ChatGPT 打法 |
| **You.com** | 自建 | 企业级多域可溯源 | 已转纯 B2B API,非 C 端引用面 |

**蓝海判断:Copilot、Brave、Mistral 是半空引用面,经典 SEO 就能打进去;头部 ChatGPT/Gemini 越来越挤。**

---

## 二、海外平台引用权重(按引擎差异化,方向性)

| 平台 | 偏好引擎 | 权重 | 适配 |
|---|---|---|---|
| **Reddit** | Perplexity 极重、ChatGPT 中、**Gemini 几乎零** | 极高 | B2C/技术/消费,UGC 讨论 |
| **Wikipedia** | ChatGPT 命脉、DuckDuckGo | 极高(偏 ChatGPT) | 通用知识/实体/定义 |
| **YouTube** | Gemini/AIO 命脉、Perplexity | 极高 | 教程/评测,带字幕转录 |
| **LinkedIn** | B2B 第一,Claude/Perplexity/ChatGPT | 高 | B2B/专业/雇主品牌 |
| **G2** | ChatGPT/Perplexity(B2B 约 75%) | 高 | B2B SaaS 评测,准入门 |
| **Capterra** | ChatGPT(B2B) | 高 | 中小企业 SaaS(已被 G2 收购) |
| **Trustpilot** | ChatGPT(消费) | 中高 | B2C/本地/低摩擦,对冲 G2 垄断 |
| **Forbes** | ChatGPT/Perplexity | 高 | 编辑类背书/B2B/财经 |
| **Stack Overflow / GitHub** | Copilot/Claude/ChatGPT | 中高 | 开发者工具/API/技术 |
| **Quora** | Gemini/ChatGPT | 中 | 问答/消费决策 |
| **Medium** | ChatGPT | 中 | 官网长文二次分发 |
| **Hacker News** | 开发/创业 | 中 | 技术/创业讨论 |
| **Yelp** | Gemini/Google(本地) | 中 | 本地服务 B2C |
| **NIH/PubMed** | Perplexity | 中 | 健康/学术 |
| **X/Twitter** | Grok 独家 | 中(仅 Grok) | 实时/社交 |
| **Substack** | 边缘 | 低 | newsletter/思想领导力 |

---

## 三、海外逐平台发布 SOP

格式对标国内:平台 × 怎么发 × 注意 × 适合谁。

**Reddit(最强跨平台,但波动大)**:遵守 90/10 规则(9 成真实贡献,1 成软推)。新号养 30 天 + 100 karma 起步,禁跨 sub 复制粘贴(会 shadowban)。适合 B2C/消费/社区品类。

**Wikipedia(ChatGPT 最高杠杆,门槛硬)**:先过 notability(5-10 条独立强引用),有付费/COI 必须披露(2025 年因未披露封号 400+),走 AfC 审核。只适合已有真实第三方报道的成熟品牌,早期初创别硬建。

**YouTube(Gemini/Perplexity 主引)**:上传**人工校对字幕**(最高杠杆,自动字幕错品牌名污染引用)。答案前置(开篇 60 秒给答案,前 30% 转录是引用区)。加章节时间戳。10-20 分钟是甜区。**最狠一招:把视频+完整转录嵌进自己官网博文(配 VideoObject schema)**,一条视频做出 3+ 引用面。

**LinkedIn(B2B 第一,最大黑马)**:发 1500-2000 字长文(短帖几乎不被引),95% 被引是原创,月发 5+。**个人页和公司页双押**(ChatGPT 偏个人 59%,Perplexity 偏公司 59%)。全资产品类用语必须一致。

**G2/Capterra/Trustpilot(B2B 评测,准入门票)**:评测是准入门不是排名杠杆(起步 5-10 条达阈值即可,别堆量,评论数与排名仅弱相关)。集中打一个主导平台。**2026-02 G2 收购了 Capterra,合体控约 55-58% 影响力,加 Trustpilot 对冲。** G2=B2B SaaS,Capterra=中小企业,Trustpilot=B2C 低摩擦,TrustRadius=企业级。

**Stack Overflow/GitHub/HN(技术内容)**:原子化可切块(每页一个概念/API),token 效率 > 关键词密度。**别挡 search-and-cite 爬虫**(挡 GPTBot/PerplexityBot/ClaudeBot 等于无法被引,要挡只挡纯训练爬虫)。适合开发者工具/API 产品。

**Medium/Quora/Substack(辅助)**:Medium 作辛迪加渠道二次分发官网长文。Quora 写自成答案的问答。Substack 是上升的 tier-3 newsletter 生态。

---

## 四、B2B vs B2C 平台选择

| 受众 | 主推平台 | 特征 |
|---|---|---|
| **B2B/SaaS** | G2(尤其 Perplexity)、Capterra、LinkedIn、行业媒体 | 长尾解决方案查询;对比页+案例+定价 |
| **B2C/消费** | Trustpilot、Reddit、YouTube、Yelp | 短产品对比查询;产品页+best-of 清单 |
| **两者通吃** | Wikipedia、跨平台一致提及、schema 地基 | 冗余跨源 |

一句话框架:**B2B 里 AI 在准备 RFP,B2C 里 AI 在准备购买。** 引用面要冗余跨源:4+ 平台一致覆盖比单一自有博文抗波动约 70 倍,82-94% 引用来自 earned media(第三方被引概率约为自有域名的 6.5 倍)。

---

## 五、多语言 / Locale

- **本地化大于翻译:** AI 能识别浅翻译(缺本地实体如税法/区域术语→低 E-E-A-T),原生写作被打高分。URL 用子目录(/de/ /fr/)+ 语言专属 schema(inLanguage + sameAs)。
- **同问不同答:** 英/德/日问同一问题,推荐品牌、引用源、详细度都不同,北美强 GEO 不自动迁移。
- **引擎语言倾向:** Claude 远比 Google 偏英文,GPT/Perplexity 更重本地语言,Gemini 较均衡。Google 内部日语本地化最强,中文是例外(英文占 >75%)。
- **战略机会:** 非英文 GEO 竞争远不如英文激烈,早动者复利建立主导引用份额。

---

## 六、海外爬虫与归因(给 attribution 升级)

爬虫分三类按用途(不按厂商):训练(GPTBot/ClaudeBot/CCBot)、检索索引(OAI-SearchBot/PerplexityBot/bingbot)、用户触发(ChatGPT-User/Claude-User/Perplexity-User,代表有人正在 AI 里读你)。

**Bing 是 Copilot/Meta AI/DuckDuckGo 共同地基**,日志里 bingbot 流量要拆归因。**UA 盲区**:Grok(住宅 IP + 伪造浏览器 UA,日志层不可见,靠 referrer grok.com/x.ai 兜底)、Copilot agent(标准 Edge UA)、Bytespider(伪造 UA)。5.7% 的 AI UA 是假的,高置信需比对官方 IP JSON。

GA4 原生 AI Assistant 频道(2026-05)只认 ChatGPT/Gemini/Claude 三家、不回填、35%-70% 无 referrer 落 Direct,所以仍需自建渠道组。详见脚本 `geo_cli attribution`。

---

## 相关

- 各引擎的内容偏好与改写战术 → [[05-engine-differences]]
- 怎么量化海外可见度 → [[06-ai-visibility-measurement]]
- 平台推荐(海外引擎) → 脚本 `geo_cli recommend --engine overseas-all`
- 中外爬虫分桶 → 脚本 `geo_cli attribution --log`
