# 案例 02 · 国内公众号深度文

## 场景

一篇讲 AI 客服降本的中文深度文,有真实数据(30 人电商、月省 2.5 万、1.2 个月回本)和场景判断,内容质量不错,但缺结构化数据,目标是被豆包、通义、腾讯元宝、DeepSeek 引用。

## 诊断要点(国内市场,求收录加占平台游戏)

- 内容有数据有案例,豆包这类拒绝无来源内容的引擎会喜欢,内容可抽取性基础好。
- 缺 FAQPage schema,丢引用率。
- robots 用 cn-index 策略:确保 Baiduspider/Sogou/bingbot 能收录,这是国产 AI 的总进水口。
- 真正的杠杆在发布:这篇要铺微信公众号(元宝独家)+ 知乎(跨 AI 最高 ROI)+ 百家号 + 今日头条。

## 工具产出(见 output/)

- `score-before.txt` / `score-after.txt` 评分对比
- `robots.txt` cn-index 策略
- `schema.html` FAQPage JSON-LD(把文中问答沉淀成结构化数据)
- `llms.txt`
- `SUMMARY.md` 改进总结 + 国内发布矩阵建议(押生态)
