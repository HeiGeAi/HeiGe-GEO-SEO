# 出海 SaaS 落地页 · 优化总结

> 一个英文 SaaS 落地页,内容偏营销话术、缺结构化数据、缺 AI 爬虫配置,目标是被 ChatGPT/Perplexity 引用。

## 评分变化

| 维度 | 优化前 | 优化后 |
|---|---|---|
| 总分 | 15/100 (危急) | 48/100 (待优化) |
| GEO 分 | 0 | 52 |
| SEO 分 | 22 | 43 |

提升 **33 分**(危急 → 待优化)。

## 目标 AI 引擎

ChatGPT、Perplexity、Claude、Google AI Overviews

## 做了什么

- robots.txt 策略:`expose-only`
- 结构化数据:`faqpage` JSON-LD(见 schema.html,已注入 optimized.html)
- llms.txt:B2A 入口(见 llms.txt)

## 发布建议(按目标引擎)

海外押 Reddit + Wikipedia,官网上结构化数据作事实锚点,有 API 文档做 llms.txt 给 agent 用户。

## 最该先修的项

- B/B2 llms-full.txt / Markdown 端点(0.0/3) · 未提供
- B/B3 ai.txt / .well-known(0.0/2) · 未提供
- C/C2 核心 schema 覆盖(WebSite/Organization/Article)(0.0/4) · 无核心 schema
