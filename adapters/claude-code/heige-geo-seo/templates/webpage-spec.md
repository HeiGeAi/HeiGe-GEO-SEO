# 模板 · 网页架构规范(Webpage Spec)

> 阶段 09 产出。给客户建/改网页的代码级 SEO+GEO 规范。详见 [[../knowledge/04-webpage-architecture]]。

---

## 页面基本信息

- 页面类型:(文章 / 问答 / 教程 / 产品 / 榜单对比 / 首页)
- 目标查询:
- 目标市场:(国内 / 海外,决定要不要 ICP/字体本地化)
- 渲染方式:(必须 SSR/SSG,CSR 禁用)

## 一、语义骨架

```html
<main>
  <article>
    <h1>(含核心查询词)</h1>
    <section aria-label="摘要"><p><strong>一句话答案:</strong>…</p></section>
    <section><h2>(语义化小标题,首段即答案)</h2>…</section>
  </article>
</main>
```

## 二、该上的 Schema(按页面类型勾选)

- [ ] Article / BlogPosting + Person(作者)+ Organization(@id 可信链)
- [ ] FAQPage(页面有真实问答时)
- [ ] HowTo(操作步骤类)
- [ ] Product + Offer/AggregateRating(产品页)
- [ ] ItemList + Product(榜单对比页)
- [ ] 全站 Organization + WebSite + BreadcrumbList

JSON-LD 由 `gen_schema.py` 生成,粘贴处:

```json

```

## 三、robots.txt(由 gen_robots.py 生成)

- 策略:(全放 / 只曝光不喂训练 / 国内求收录)

```

```

## 四、llms.txt(可选,由 gen_llms_txt.py 生成)

- 做不做:(开发者工具+agent 用户→做;营销站→跳过)

```

```

## 五、技术地基自查

- [ ] 核心正文 SSR/SSG,`curl -A "ClaudeBot"` 能看到完整正文
- [ ] sitemap.xml 带 lastmod 并提交各平台
- [ ] 每页 canonical
- [ ] 移动响应式 + Core Web Vitals 达标
- [ ] 国内站:ICP 备案 + 页脚备案号 + 字体本地化 + 国内 CDN

## 六、可抽取性自查

- [ ] TL;DR 一句话答案块,自包含
- [ ] 每个 H2 首段即答案
- [ ] 真实问句当标题 + 直答
- [ ] 关键术语有"X 是……"定义块
- [ ] 段落短(2~4 句),数据点带真实出处

## 七、E-E-A-T 自查

- [ ] 具名作者 + 独立作者页 + sameAs
- [ ] 发布/更新时间双标注
- [ ] 关键论断有引用和权威外链
- [ ] 有第一手数据/案例/原创图表
