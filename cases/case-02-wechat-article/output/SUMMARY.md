# 国内公众号深度文 · 优化总结

> 一篇讲 AI 客服降本的中文深度文,内容有真实数据和案例,但缺结构化数据,目标是被豆包、通义、腾讯元宝、知乎引用。

## 评分变化

| 维度 | 优化前 | 优化后 |
|---|---|---|
| 总分 | 43/100 (待优化) | 67/100 (待优化) |
| GEO 分 | 34 | 70 |
| SEO 分 | 36 | 56 |

提升 **24 分**(待优化 → 待优化)。

## 目标 AI 引擎

豆包、通义千问、腾讯元宝、DeepSeek

## 做了什么

- robots.txt 策略:`cn-index`
- 结构化数据:`faqpage` JSON-LD(见 schema.html,已注入 optimized.html)
- llms.txt:B2A 入口(见 llms.txt)

## 发布建议(按目标引擎)

国内押生态多平铺:**知乎(最高 ROI)+ 微信公众号(元宝独家)+ 百家号(文心)+ 今日头条(豆包)**。
一稿四态:深度长文、知乎问答体、小红书短图文、视频带字幕。详见知识库 03-publishing-channels。

## 最该先修的项

- B/B2 llms-full.txt / Markdown 端点(0.0/3) · 未提供
- B/B3 ai.txt / .well-known(0.0/2) · 未提供
- C/C2 核心 schema 覆盖(WebSite/Organization/Article)(0.0/4) · 无核心 schema
