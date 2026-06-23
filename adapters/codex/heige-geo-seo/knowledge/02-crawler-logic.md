# 知识库 02 · 抓取逻辑库

> 这是 HeiGe-GEO-SEO 最核心的原创差异点。市面上所有英文 GEO 工具都只教你配 robots.txt 放行 GPTBot,**那套在中国基本失效**。中国和海外是两套完全不同的游戏。

核查日期 2026-06。结论先行,可执行打法在每块末尾。

---

## 一句话总览

**海外 AI 普遍自建爬虫、有公开 UA,写进 robots.txt 就能精确控制。中国 AI 基本不自建公开爬虫,实时内容靠借道第三方搜索 API(博查、搜狗、必应)和绑自家内容生态,robots.txt 对它们几乎不起作用。想被国内 AI 抓到,关键是被百度/必应/搜狗收录 + 进高权重平台,而不是开放 robots。**

一句话记住:**国内 GEO 是求收录 + 占平台的游戏,海外 GEO 是配 robots.txt 的游戏。**

---

## 第一块 · 中国抓取逻辑(重点)

### 国内 AI 拿实时内容的三条真实路径

国内主流 AI 几乎没有一个像 GPTBot 那样满网爬公开网页的自有实时爬虫。它们的实时内容走这三条路,且常常混用:

| 路径 | 机制 | 谁在用 | 对 GEO 的含义 |
|---|---|---|---|
| **借道第三方搜索 API** | 模型联网时调搜索接口拿 URL + 摘要,再抓正文喂模型 | DeepSeek(官方 App)、大量第三方 AI 应用 | 内容必须先被这个搜索引擎收录 |
| **借道自家搜索引擎索引** | 直接吃自家搜索引擎已经爬好的网页库 | 文心(百度)、元宝(搜狗)、豆包/Kimi(部分接必应) | 内容必须被百度/搜狗/必应收录 |
| **绑自家内容生态** | 优先吃自己平台的结构化内容,不依赖公网爬取 | 豆包吃抖音+头条、文心吃百度系、通义吃阿里系、元宝吃公众号 | 内容进对应平台 = 被优先喂给该 AI |

**已取证的关键事实:**

- **DeepSeek 及国内 60%+ 的 AI 应用,联网搜索靠博查(Bocha)AI 的 Search API 实现。** 博查是目前国内唯一专给 AI 用的搜索 API,被当成"国内版 Bing Search API"的事实标准。大量国产 AI 的"眼睛"其实是同一个搜索源。
- **腾讯云 DeepSeek API 与元宝**走搜狗搜索增强 API。
- **文心一言**接百度搜索插件,实时性等于百度收录范围。
- **DeepSeek 官方 API 默认不带联网**,联网是网页端/第三方自己接搜索 API 加的。"被 DeepSeek 引用"本质是"被它接的那个搜索 API 收录"。

### 字节系是国内唯一有公开爬虫 UA 的玩家

**Bytespider** 是国内唯一能在日志里抓到的、带明确标识的 AI 相关爬虫:

```
Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)
```

它服务头条搜索 + 豆包内容库。**重要警告:Bytespider 名义上读 robots.txt,实测被大量站长记录为不尊重、抓取极激进。** 想挡只能 `User-agent: Bytespider / Disallow: /` 加防火墙层 IP/UA 双拦,光靠 robots.txt 经常无效。

除 Bytespider 外,豆包/文心/通义/Kimi/元宝**没有对外公开、可在日志识别的实时爬虫 UA**。它们抓正文要么走搜索 API(UA 是 Baiduspider/Sogou web spider/bingbot 或普通浏览器),要么走自家生态内部接口(根本不出公网)。

### robots.txt 在国内基本不是有效控制手段

- 国产 AI 没有 `Google-Extended` 这种"训练专用控制 token",你**无法用 robots.txt 精确屏蔽某个国产大模型的训练**。
- 你能控制的只有真正的搜索引擎爬虫:`Baiduspider`、`Sogou web spider`、`bingbot`。挡了它们等于退出百度/搜狗/必应索引,也就退出了文心/元宝/DeepSeek 的实时来源。**所以国内 GEO 几乎永远是求收录,而不是防抓取。**

### 中文内容被国内 AI 收录的关键前提(最该写进规则)

按重要性排序:

1. **先被搜索引擎收录,这是地基。** 被**百度收录**(覆盖文心、百度系)、被**必应收录**(覆盖博查/部分豆包 Kimi 来源)、被**搜狗收录**(覆盖元宝、腾讯云 DeepSeek)。三个里至少占两个,你才在国产 AI 的可见区里。
2. **进高权重平台,这是放大器,国内比海外更关键。** 取证明确:**国内 AI 引用独立企业/个人网站极少,强烈偏好权威媒体、自媒体、大型社区。** 同一份内容挂自己官网可能永远不被引,发到知乎/公众号/百家号/抖音头条就会被引。
3. **ICP 备案,隐性门槛。** 没备案的站在国内 CDN、可访问性、被国内搜索引擎正常收录上都吃亏,间接拉低被国产 AI 抓到的概率。**做国内 GEO,备案是基础卫生。**

### 中国部分 · 配置打法

想被国内 AI 抓到,优先级从高到低:

- **不要**在 robots.txt 里屏蔽 `Baiduspider` / `Sogou web spider` / `bingbot`,确保三大索引都能进。这是国产 AI 的总进水口。
- 核心结论内容**同步分发到知乎 + 微信公众号 + 百家号**,而不是只放官网。国内被引靠平台权重,不靠你的域名。
- 想吃豆包进**抖音/头条生态**,想吃文心进**百度系**,想吃元宝走**公众号**。
- 站点**完成 ICP 备案**,用国内可正常访问的托管。
- 内容结构:**开头 150~220 字给出可复述的结论句,一篇只服务一个意图,先结论后解释**,无论被哪个搜索 API 抓去做 RAG,正文都好抽取、好被引。
- 唯一能硬挡的国产 AI 爬虫是 Bytespider,要 robots + 防火墙双层。

---

## 第二块 · 海外爬虫清单(含真实 UA)

UA token 拼写按官方文档核实。三类用途:**Train 喂训练 / Search 建检索索引 / User 用户当场点了才抓单页。**

### OpenAI(三机分工,最规范)

| UA token | 用途 | robots.txt | 真实 UA |
|---|---|---|---|
| **GPTBot** | Train | 遵守 | `...compatible; GPTBot/1.2; +https://openai.com/gptbot` |
| **OAI-SearchBot** | Search | 遵守 | `...compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot` |
| **ChatGPT-User** | User | 遵守 | `...compatible; ChatGPT-User/1.0; +https://openai.com/bot` |

打法:想进 ChatGPT 引用但不喂训练,**Allow `OAI-SearchBot` + Disallow `GPTBot`**(OpenAI 官方认可)。

### Anthropic

| UA token | 用途 | robots.txt | 真实 UA |
|---|---|---|---|
| **ClaudeBot** | Train | 遵守 | `Mozilla/5.0 (compatible; ClaudeBot/1.0; claudebot@anthropic.com)` |
| **Claude-SearchBot** | Search | 遵守 | token `Claude-SearchBot` |
| **Claude-User** | User | 遵守 | `...compatible; Claude-User/1.0; ...` |

`Claude-Web` / `anthropic-ai` 是旧 token,现已统一为 ClaudeBot 三件套。屏蔽时可把旧 token 一起写以兼容历史日志。

### Perplexity

| UA token | 用途 | robots.txt | 真实 UA |
|---|---|---|---|
| **PerplexityBot** | Search | 文档称遵守,**实测有不合规记录** | `...compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot` |
| **Perplexity-User** | User | 文档称遵守,**实测不一致** | `...compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user` |

警告:Perplexity 被多方记录会无视 robots.txt、用住宅 IP 绕过。要真挡得上防火墙。

### Google

| UA token | 用途 | robots.txt | 备注 |
|---|---|---|---|
| **Googlebot** | Search | 遵守 | 被搜索收录的总闸 |
| **Google-Extended** | Train 开关 | 仅控制 token | **不是爬虫,日志看不到**;Disallow 它=拒绝 Gemini/Vertex 训练,不影响搜索收录 |
| **Google-CloudVertexBot** | Search | 遵守 | Vertex AI 抓取 |
| **Google-NotebookLM 等 user-triggered** | User | **不遵守 robots.txt** | 用户触发类一律绕过 |

打法:想留在 Google/Gemini 搜索但不喂训练,留 `Googlebot`,**Disallow `Google-Extended`**。

### 微软 / Bing(同时喂 Copilot)

| UA token | 用途 | robots.txt | 真实 UA |
|---|---|---|---|
| **bingbot** | Search(Bing + Copilot 共用) | 遵守 | `...compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm` |

**bingbot 是海外加国内的双料关键:** Bing 索引同时供 Copilot、博查、部分国产 AI 的海外来源。**别屏蔽 bingbot。**

### 其它主流

| 公司 | UA token | 用途 | robots.txt | 真实 UA |
|---|---|---|---|---|
| Amazon | **Amazonbot** | Train + 检索 | 遵守 | `...compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot...` |
| Apple | **Applebot** | Search(Siri/Spotlight) | 遵守 | `...Applebot/...; +http://www.apple.com/go/applebot` |
| Apple | **Applebot-Extended** | Train 控制 token | 控制 token | Disallow=拒绝 Apple Intelligence 训练,不影响 Siri 收录 |
| Meta | **Meta-ExternalAgent** | Train + AI 索引 | 遵守 | `meta-externalagent/1.1 (+https://developers.facebook.com/...)` |
| Common Crawl | **CCBot** | Train 语料(被几乎所有人二次用) | 遵守 | `CCBot/2.0 (https://commoncrawl.org/faq/)` |
| DuckDuckGo | **DuckAssistBot** | Search | 遵守,不用于训练 | `...compatible; DuckAssistBot/1.0; ...` |
| Mistral | **MistralAI-User** | User | 遵守 | `...compatible; MistralAI-User/1.0; +https://docs.mistral.ai/robots` |
| 字节 | **Bytespider** | Train(报告) | **名义遵守,实测不遵守** | `Mozilla/5.0 (compatible; Bytespider; ...bytedance.com)` |
| xAI | Grok 爬虫 | Train/检索(报告) | **无文档,住宅 IP + 伪造 UA** | 无固定 token,难识别 |

### 海外部分 · 配置打法

**全放(最大化 AI 可见度,推荐给做 GEO 的内容方):** 什么都不屏蔽,确保 GPTBot/OAI-SearchBot、ClaudeBot 三件套、PerplexityBot、bingbot、Googlebot、Amazonbot、Applebot 都能进。

**只要曝光、不喂训练(典型 GEO 诉求):**

```
# 进 ChatGPT 但不喂 OpenAI 训练
User-agent: OAI-SearchBot
Allow: /
User-agent: GPTBot
Disallow: /

# 留在 Google/Apple 搜索,拒绝其 AI 训练(控制 token)
User-agent: Google-Extended
Disallow: /
User-agent: Applebot-Extended
Disallow: /

# 保留搜索可见度
User-agent: Googlebot
Allow: /
User-agent: bingbot
Allow: /
User-agent: Applebot
Allow: /
```

**真要拦脏爬虫(Bytespider / PerplexityBot / Grok):robots.txt 不够,必须上防火墙按 UA + IP 拦。**

两个反复踩的坑:

1. **屏蔽一个 bot 不会连带屏蔽同公司其它 bot。** GPTBot、OAI-SearchBot、ChatGPT-User 要分别写,这是最常见的配置错误。
2. **`*-Extended` 和 `*-User` 类不是爬虫。** `Google-Extended` 是训练开关、日志永远看不到;`ChatGPT-User` 是用户当场触发、不遵守常规 robots 节奏。别拿管爬虫的思路管它们。

---

## 给优化决策的两条核心规则(最高优先级)

1. **海外 = robots.txt 精确控制游戏。** UA 公开,`Allow OAI-SearchBot + Disallow GPTBot` 这类组合直接有效。工具做"robots.txt 体检 + 一键生成最优 AI 抓取策略"。
2. **国内 = 求收录 + 占平台游戏,robots.txt 基本失效。** 国产 AI 没公开爬虫,靠博查/搜狗/必应/百度的索引和自家生态。国内模块该检查的是"百度/必应/搜狗收录状态 + 是否进知乎/公众号/百家号 + ICP 备案",而不是检查 robots.txt。

---

## 国产搜索引擎爬虫 UA 清单(v1.4 补,对称海外表)

国内能在日志里识别的搜索/AI 爬虫,放行这些等于打通国产 AI 的索引进水口:

| UA token | 归属 | 喂哪个 AI / 搜索 | robots |
|---|---|---|---|
| `Baiduspider` | 百度 | 百度搜索 + 文心 | 遵守 |
| `Sogou web spider` | 搜狗 | 搜狗 + 腾讯元宝 | 遵守 |
| `YisouSpider` | 神马(UC/夸克) | 神马移动搜索 + 夸克 + 通义 | **名义遵守,实测多投诉不遵守(同 Bytespider,抓取激进)** |
| `360Spider` / `HaoSpider` | 360 | 360 搜索 + 360 AI | 遵守 |
| `Bytespider` | 字节 | 头条搜索 + 豆包 | **名义遵守,实测不遵守** |
| `PetalBot` | 华为 | 花瓣搜索 + 盘古 | 遵守 |

**配置:cn-index 策略(`gen_robots.py --strategy cn-index`)已放行 Baiduspider/Sogou/神马/360/Bingbot,这是国产 AI 的总进水口,别屏蔽。** 日志分桶用 `attribution --log` 区分国内 vs 海外。

## 相关知识库

- 这些 AI 各自吃哪个生态 → [[01-llm-landscape]]
- 进哪些平台能被国内 AI 收录 → [[03-publishing-channels]]
- robots.txt 与 SSR 等技术地基怎么落地 → [[04-webpage-architecture]]
- 自动生成最优 robots.txt → 脚本 `gen_robots.py`
