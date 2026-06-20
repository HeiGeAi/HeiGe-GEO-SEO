# 案例 03 · 国内产品页

## 场景

一个中文产品页(智能排版器,公众号排版工具),有功能列表和定价,目标是命中"最好的公众号排版工具""公众号怎么快速排版"这类查询,被豆包、文心、通义推荐。

## 诊断要点

- 产品页要被 AI 当"最好的 X"推荐,关键是上 `Product` schema(带 Offer 价格和 AggregateRating 评分),让 AI 抽到结构化产品事实。
- 内容有具体数字(30 种主题、39 元、2 万作者、30 分钟降到 1 分钟),可抽取性好,符合豆包对有数据内容的偏好。
- robots 用 cn-index 确保百度收录(文心走百度索引)。
- 发布上把产品介绍铺成知乎"公众号排版工具怎么选"问答 + 小红书种草。

## 工具产出(见 output/)

- `score-before.txt` / `score-after.txt`
- `robots.txt` cn-index
- `schema.html` Product JSON-LD(带价格和评分)
- `llms.txt`
- `SUMMARY.md`
