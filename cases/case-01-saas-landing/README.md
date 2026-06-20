# 案例 01 · 出海 SaaS 落地页

## 场景

一个英文 SaaS 落地页 FlowDesk,内容偏营销话术("we are the best""you will not regret"),没有结构化数据,没给 AI 爬虫配 robots.txt,目标是被 ChatGPT、Perplexity、Claude、Google AI Overviews 引用。

## 诊断要点(海外市场,配 robots.txt 游戏)

- 内容是营销话术,缺可被引用的事实、定义、统计。这类内容 AI 引擎不爱引。
- 没有 FAQPage schema,丢掉 2.7 倍引用率机会。
- 没有 robots.txt,无法显式放行 AI 检索爬虫。
- 没有 llms.txt(开发者类受众,可做)。

## 工具产出(见 output/)

- `score-before.txt` 基线评分
- `robots.txt` 只曝光不喂训练策略(放行 OAI-SearchBot/Claude-SearchBot/PerplexityBot,拒绝 GPTBot/ClaudeBot 训练)
- `schema.html` FAQPage JSON-LD,把营销话术重写成可被抽取的问答对
- `llms.txt` B2A 入口(SaaS 有 API 文档,值得做)
- `score-after.txt` 加上 robots + llms 后的复评
- `SUMMARY.md` 改进总结与发布建议

跑法:`python3 ../run_cases.py`(在 cases/ 目录),或单跑本案例 `python3 ../run_cases.py case-01-saas-landing`。
