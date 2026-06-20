# 知识库 04 · 网页架构库

> 这是 HeiGe-GEO-SEO 的"网页制作建议"模块。面向既要被搜索引擎收录排名、又要被 AI 引擎(ChatGPT/Claude/Perplexity/Google AI Overview/百度文心)抓取引用的网页。**所有建议给到代码级,可直接复制改用。** 核查日期 2026-06。

---

## 一句话判断标准

**一个页面能不能被 AI 引用,取决于三件事:爬虫能不能拿到完整内容(技术可达)、内容能不能被切成独立可引用的块(可抽取性)、来源可不可信(E-E-A-T)。** SEO 和 GEO 的底层要求高度重合,GEO 只额外要求"答案前置 + 结构化分块 + 来源可追溯"。

一组定方向的数据:Article + BlogPosting schema 组合出现在 76% 的 Google AI Mode 引用页面里(Search Atlas 对 107,352 个被引网站统计);AI 搜索访问量同比增长 42.8%。**GEO 已经是必须做,不是可选项。**

---

## 1. 语义化 HTML5 结构

不渲染 JS 的 AI 爬虫只看初始 HTML 的标签语义。`<article>`、`<section>`、正确的 `h1-h6` 层级,就是告诉爬虫哪段是主体、哪段是噪音、逻辑骨架长什么样。语义标签是 AI 切块抽取的天然分隔符。

**硬规则:**

- **每页有且只有一个 `<h1>`**,对应主题,文字含核心查询词。
- **标题层级不跳级**,h2 下面才是 h3,不为样式从 h2 直接跳 h4。
- **正文主体包在 `<main><article>` 里**,导航 `<nav>`、页眉 `<header>`、页脚 `<footer>`、侧栏 `<aside>` 各归各位。
- **每个 `<section>` 配一个语义化标题**("如何配置 robots.txt"而不是"步骤三")。
- 列表用 `<ul>/<ol>`、表格用 `<table>`,不要用 `<div>` 模拟。

```html
<body>
  <header><nav aria-label="主导航"><!-- 站点导航 --></nav></header>
  <main>
    <article>
      <h1>网页如何同时做好 SEO 和 GEO</h1>
      <section aria-label="摘要">
        <p><strong>一句话答案:</strong>……</p>
      </section>
      <section>
        <h2>语义化结构怎么做</h2>
        <p>……</p>
        <h3>标题层级规则</h3>
        <p>……</p>
      </section>
      <section>
        <h2>常见问题</h2>
        <!-- 明确问答对,配 FAQPage schema -->
      </section>
    </article>
    <aside aria-label="相关阅读"><!-- 非主体 --></aside>
  </main>
  <footer><!-- 版权、备案号、更新时间 --></footer>
</body>
```

---

## 2. schema.org 结构化数据(JSON-LD)

**选型原则:**

- **统一用 JSON-LD**,放 `<head>` 或 body 末尾的 `<script type="application/ld+json">`。不要用 Microdata/RDFa。
- **能链接就别内联:** Person、Organization 用 `@id` 互相引用,构成"作者→机构→社媒认证"的可信链,这是 AI 判断来源可信度的核心路径。
- **别堆砌不真实的 schema:** 标了 FAQPage 页面却没问答会被判作弊。schema 必须和可见内容一一对应。

**按页面类型该上哪些(GEO 优先级表):**

| 页面类型 | 必上 | 建议上 | GEO 价值 |
|---|---|---|---|
| 文章/博客/教程 | `Article` 或 `BlogPosting` + `Person`(作者) + `Organization` | `BreadcrumbList` | 最高,占 AI Mode 引用页 76% |
| 问答/帮助页 | `FAQPage` 或 `QAPage` | `BreadcrumbList` | 高,AI 直接抽问答对 |
| 操作步骤/教程 | `HowTo` | `Article` | 高,AI 抽步骤列表 |
| 产品/工具页 | `Product` + `AggregateRating`/`Offer` | `Review` | 高,"最好的 X"类查询命中 |
| 榜单/对比页 | `ItemList` + 每项 `Product` | `Article` | 高,"best X"类查询直接被引 |
| 全站每页 | `Organization` + `WebSite` | `BreadcrumbList` | 中,建可信实体 |

`FAQPage` 用于页面自己提供的多组问答,`QAPage` 用于一个用户提问加多个回答的社区页,两者不混用。`Speakable` 仅语音/播客场景加。

**示例 1 · Article + 作者可信链(GEO 主力):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "网页如何同时做好 SEO 和 GEO",
  "description": "面向被 AI 引擎引用的网页架构与内容规范。",
  "datePublished": "2026-06-20T09:00:00+08:00",
  "dateModified": "2026-06-20T09:00:00+08:00",
  "mainEntityOfPage": { "@type": "WebPage", "@id": "https://example.com/seo-geo-guide" },
  "author": {
    "@type": "Person",
    "@id": "https://example.com/about#author",
    "name": "张三",
    "jobTitle": "首席技术官",
    "knowsAbout": ["SEO", "生成式引擎优化", "Web 架构"],
    "sameAs": ["https://www.linkedin.com/in/zhangsan", "https://x.com/zhangsan"]
  },
  "publisher": {
    "@type": "Organization",
    "@id": "https://example.com/#org",
    "name": "示例科技",
    "logo": { "@type": "ImageObject", "url": "https://example.com/logo.png" }
  }
}
</script>
```

关键:`datePublished`/`dateModified` 用 ISO 8601 带时区;`author` 用 `@id` 指向真实作者页;`sameAs` 链到可验证社媒。这条链越完整,被引概率越高。

**示例 2 · FAQPage(AI 直接抽问答对):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "AI 爬虫会执行 JavaScript 吗?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "大多数不会。ClaudeBot、GPTBot 默认不渲染 JavaScript,只读初始 HTML。核心内容必须服务端渲染或静态生成,确保首屏 HTML 里就有完整正文。"
      }
    }
  ]
}
</script>
```

页面上必须有对应的可见问答文本,schema 只是机器可读副本。

**示例 3 · HowTo(AI 抽步骤):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "如何为 AI 爬虫配置 robots.txt",
  "step": [
    { "@type": "HowToStep", "position": 1, "name": "列出目标爬虫", "text": "确定放行 GPTBot、ClaudeBot、PerplexityBot 等。" },
    { "@type": "HowToStep", "position": 2, "name": "写 Allow 规则", "text": "为每个 user-agent 写明放行路径。" },
    { "@type": "HowToStep", "position": 3, "name": "验证", "text": "用日志确认爬虫实际抓取行为。" }
  ]
}
</script>
```

`gen_schema.py` 脚本可自动生成以上四类 JSON-LD,直接调用。

---

## 3. 答案前置 / 倒金字塔 / TL;DR 块

AI 生成回答时优先从"能独立成立、直接回答问题"的段落取材。倒金字塔把结论放最前,爬虫在开头就拿到可直接引用的整句。靠后才出结论的文章,AI 要么读不到(被截断),要么不敢用(缺乏自包含语境)。

**硬规则:**

- **每页顶部放一个 TL;DR 块**,40~60 字内直接回答标题问题,能脱离上下文独立成立。
- **每个 `<h2>` 小节第一段就是该小节的答案**,后面再展开(小节内也倒金字塔)。
- **答案句写成完整陈述句**,主谓宾齐全,不用"如上所述""见下文"这类指代。AI 抽出来要能直接当一句话用。
- 用 `<strong>` 标出每个答案句,给读者也给爬虫一个"这是重点"的信号。

---

## 4. 内容分块与可抽取性

**把页面写成一堆可独立搬走的乐高块,而不是一篇必须从头读到尾的散文。** AI 抽取的最小单位是段落/列表项/表格行,块越自包含,越容易被精准引用且不被曲解。经验值:每 300 字含 2~3 个数据点,与被 AI 引用率正相关。

**可抽取性清单:**

- **短段落:** 一段一个观点,2~4 句。长段落 AI 难切。
- **列表化流程:** 步骤、清单、要点用 `<ol>/<ul>`,AI 抽列表成功率远高于抽散文。
- **表格化对比:** 任何 A vs B、多维对比用 `<table>` 且首行 `<th>`,表格是 AI 解析引用准确度最高的结构之一。
- **明确问答对:** 用户真实会问的话当 `<h2>/<h3>` 标题("X 是什么""怎么做 Y""X 和 Y 的区别"),紧接直答段落,配 FAQ schema 双保险。
- **定义块:** 关键术语首次出现给一句"X 是……"标准定义,AI 回答"X 是什么"时优先抓这种句子。
- **数据点带出处:** 句子里嵌具体数字加来源,比泛泛而谈更易被引。
- **自包含:** 每个块内部不依赖前文指代,补全必要主语。

---

## 5. E-E-A-T 信号(经验·专业·权威·可信)

AI 引用前会评估来源可信度,E-E-A-T 落到页面就是一组机器可读的具体信号。

- **真实作者署名:** 每篇有具名作者,链到独立作者页(带 `jobTitle`、`knowsAbout`、`sameAs`)。匿名内容 AI 引用意愿低。
- **作者→机构→社媒的 `@id` 可信链**(见第 2 节示例 1),让 AI 能溯源验证。
- **发布与更新时间双标注:** 页面可见处 + schema 的 `datePublished`/`dateModified`。建议 7~14 天回看更新一次。
- **引用与外链:** 关键论断标来源,外链权威站点。带引用的内容被 AI 当作有据可查。
- **第一手经验信号:** 实测数据、案例、截图、原创图表。这是 E-E-A-T 第一个 E(Experience),AI 难从别处复制,引用价值最高。
- **机构信息透明:** 关于页、联系方式、备案信息齐全。

---

## 6. 技术 SEO 基础(GEO 的地基)

### 6.1 SSR vs CSR,GEO 的生死线

**主流 AI 爬虫默认不执行 JavaScript。** ClaudeBot、GPTBot 等只读初始 HTML。

| 渲染方式 | AI 爬虫可见性 | 结论 |
|---|---|---|
| CSR 纯客户端 | 几乎不可见(拿到空 `<div id="root">`) | GEO 禁用 |
| SSR 服务端渲染 | 完整可见 | 推荐 |
| SSG 静态生成 | 完整可见 + 最快 | 内容型页面首选 |
| 动态渲染(给爬虫返预渲染) | 可见但维护成本高 | 过渡方案 |

验证方法:`curl -A "ClaudeBot" https://你的页面` 看返回 HTML 里有没有正文。看不到正文等于 AI 引用不了。

### 6.2 robots.txt,给 AI 爬虫开门

要被 AI 引用至少放行检索类和用户实时拉取类(`OAI-SearchBot`/`Claude-SearchBot`/`PerplexityBot` 及对应 `*-User`)。是否放行训练类(`GPTBot`/`ClaudeBot`)按版权立场定。具体 UA 清单和一键生成见 [[02-crawler-logic]] 和 `gen_robots.py`。

注意:Bytespider、Perplexity 隐身爬虫曾被记录无视 robots.txt。robots.txt 是约定不是强制,敏感内容靠它防不住,要靠服务端鉴权。

### 6.3 sitemap.xml

列出所有要收录的 URL,提交 Google Search Console、Bing、百度搜索资源平台。每条带 `<lastmod>`。

### 6.4 canonical 规范化

每页 `<head>` 声明权威 URL,避免重复内容分散权重、避免 AI 引到错误变体:

```html
<link rel="canonical" href="https://example.com/seo-geo-guide" />
```

### 6.5 移动优先 + 加载速度

- 响应式 + viewport meta,Google/百度都移动优先索引。
- Core Web Vitals 达标:LCP < 2.5s、CLS < 0.1、INP < 200ms。
- 图片 WebP/AVIF + 懒加载,关键 CSS 内联,JS 延迟加载,但正文不能依赖 JS。

### 6.6 必备 head 元信息

```html
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>页面标题(含核心查询词,≤60 字符)</title>
  <meta name="description" content="一句话描述,含答案,≤155 字符,AI 会用作摘要" />
  <link rel="canonical" href="https://example.com/seo-geo-guide" />
  <meta property="og:title" content="..." />
  <meta property="og:type" content="article" />
</head>
```

---

## 7. llms.txt 文件(诚实定性)

**截至 2026 年,llms.txt 仍是社区提案,无任何标准组织背书,OpenAI/Google/Anthropic/Meta 均未公开承诺在生产系统里读取它。** Google 明确说不支持,把它类比已废弃的 keywords meta 标签。大规模实测(Ahrefs 13.7 万站点)显示 97% 的 llms.txt 收到零请求。

**结论:把它当低成本、可选、未来可能有用的项,做一份放着,别为它投入大量精力,更别向用户承诺它能提升排名。**

- 营销站/内容站做 AI 搜索曝光:**不做**,时间投到内容质量和结构化数据上。
- 开发者工具 + 大量 API 文档 + agent 用户:**做且认真做**,这是它唯一被实证持续使用的场景(IDE agent、MCP、agentic 工作流会真去抓它当结构化入口)。
- 用 Mintlify 类平台托管文档:**零成本拿着**,平台自动生成。

定性一句话:**llms.txt 不是 SEO 资产,是 B2A(business-to-agent)基础设施。** 判断该不该做只看一个问题:你的用户会不会用 AI agent 直接访问你的文档。会就做,不会就跳过。模板见 `gen_llms_txt.py`。

---

## 8. 中国特色:百度收录 + ICP 备案 + 国内访问速度

### 8.1 ICP 备案(国内服务器硬门槛)

- **服务器在中国大陆等于必须先完成 ICP 备案才能开站**,未备案直接被运营商阻断。
- 公安联网备案在 ICP 备案成功后 30 天内完成。
- 用国内 CDN 时被加速域名同样要备案。
- 备案号展示在页脚(合规 + 给百度和用户可信信号):

```html
<footer>
  <a href="https://beian.miit.gov.cn/" target="_blank" rel="nofollow">京ICP备XXXXXXXX号-1</a>
</footer>
```

- 想跳过备案就把服务器放境外/香港,代价是国内访问慢、百度收录受影响。做国内市场就老实备案。

### 8.2 百度收录要点

- **主动推送:** 用百度搜索资源平台链接提交(API/sitemap/手动),别干等爬虫。新站收录通常 7~15 天。
- 百度爬虫是 `Baiduspider`,robots.txt 单独放行。
- 百度重视原创保护,伪原创/采集会被压制。
- 百度 AI 搜索(文心)同样靠结构化数据判断内容可否被准确抽取,`ItemList` + `Product` 对"最好的 X"类查询命中尤其有效。

### 8.3 国内访问速度

- 国内 CDN(阿里云/腾讯云/百度云加速)就近分发。
- **字体坑:别用 Google Fonts(国内被墙,拖慢甚至卡死首屏),字体本地化自托管。**
- 静态资源走国内对象存储 + CDN,别引境外 CDN 的 JS/CSS。

---

## 附录:SEO+GEO 友好网页上线前自查清单

**技术可达性(爬虫拿不到内容,下面全白做)**

- [ ] 核心正文 SSR/SSG,`curl -A "ClaudeBot"` 能看到完整 HTML 正文
- [ ] robots.txt 放行 AI 检索爬虫(OAI-SearchBot / Claude-SearchBot / PerplexityBot + 对应 *-User)
- [ ] sitemap.xml 存在、带 lastmod、已提交各搜索平台
- [ ] 每页 canonical 正确
- [ ] 移动响应式 + viewport,Core Web Vitals 达标
- [ ] 国内站:ICP 备案 + 页脚备案号 + 字体本地化 + 国内 CDN

**结构与语义**

- [ ] 单一 h1,h2-h6 不跳级
- [ ] 主体在 `<main><article>`,噪音在 `<nav>/<aside>/<footer>`
- [ ] 列表用 `<ul>/<ol>`,对比用 `<table>` 带 `<th>`

**可抽取性**

- [ ] 顶部有 TL;DR 一句话答案块,自包含
- [ ] 每个 h2 小节首段即答案
- [ ] 真实用户问句当标题 + 直答段落
- [ ] 关键术语有"X 是……"定义块
- [ ] 段落短(2~4 句),数据点带出处

**结构化数据**

- [ ] 上了匹配页面类型的 schema(Article/FAQPage/HowTo/Product/ItemList)
- [ ] Article 配 Person + Organization 的 @id 可信链
- [ ] datePublished/dateModified ISO 8601 带时区
- [ ] 全站 Organization + WebSite + BreadcrumbList
- [ ] schema 内容和页面可见内容一一对应(不造假)

**E-E-A-T**

- [ ] 具名作者 + 独立作者页 + sameAs 社媒
- [ ] 页面可见处标注发布/更新时间,定期回看
- [ ] 关键论断有引用和权威外链
- [ ] 有第一手数据/案例/原创图表

**可选**

- [ ] /llms.txt 做一份(低成本,不当排名因子)

---

## 相关知识库

- 不同 AI 对页面的偏好差异 → [[01-llm-landscape]]
- robots.txt 完整 UA 清单与国内收录逻辑 → [[02-crawler-logic]]
- 官网这一版怎么配合多渠道分发 → [[03-publishing-channels]]
- GEO 改写方法与评分卡 → [[../methodology/geo-methods]] · [[../methodology/scoring-card]]
