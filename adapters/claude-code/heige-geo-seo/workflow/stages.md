# 工作流 · 十阶段 GEO+SEO 优化流程

> 这是 HeiGe-GEO-SEO 干活的主干流程,把"调研 → 改写 → 评分 → 发布 → 复审"做成可复现的十个阶段。综合 recomby-geo 的七阶段编排和 seo-geo-claude-skills 的生命周期分层。**两个人工 checkpoint 不可绕过,这是合规 GEO 区别于内容投毒的核心。**

---

## 流程总览

```
01 Intake 接入       吃业务材料,结构化建项目
02 Research 调研      关键词 / 对手 / 目标 AI 引擎 / 内容缺口
03 Audit 基线审计     隔离评估当前 GEO 就绪度,打基线分
04 Brief 内容简报     搭框架 + 留专家洞察槽位        ★人工 checkpoint 1
05 Build 生产         写稿 + GEO 改写 + TDK + Schema
06 Optimize 优化      页面/技术审计 + 内链 + 旧文刷新
07 QualityGate 质量门  跑评分卡 + GEU 护栏,SHIP/FIX/BLOCK  ★人工 checkpoint 2
08 Distribute 分发     按渠道矩阵给发布建议
09 WebSpec 网页规范    给网页架构与代码级建议
10 Re-audit 复审       发布 7 天后回看效果,反哺 02
```

不是每个任务都要跑满十步。轻量任务(只优化一篇已有内容)可跳到 03→05→07;完整客户交付走全程。

---

## 阶段详解

### 01 Intake 接入

吃进业务材料(URL/PDF/笔记/现有内容),结构化进项目。明确三件事:**目标 AI 引擎**(打豆包还是 ChatGPT,决定整套打法,见 [[../knowledge/01-llm-landscape]])、**目标市场**(国内还是海外,决定抓取逻辑,见 [[../knowledge/02-crawler-logic]])、**内容域**(决定选哪些改写方法,见 [[../methodology/geo-methods]])。

输出:项目档案,含目标引擎清单、市场、域、现有素材。

### 02 Research 调研

- 关键词与用户真实问句(GEO 看的是"用户会怎么问 AI",不只是搜索关键词)
- 竞品在目标 AI 回答里被引用的情况
- 内容缺口:哪些用户高频问题还没有好内容覆盖

输出:关键词与问句清单、竞品引用现状、内容缺口表。

### 03 Audit 基线审计

**用隔离评估,不带客户自述的滤镜**,跑当前内容/页面的 GEO 就绪度,用 `geo_score.py` 打基线分(6 维 22 项,见 [[../methodology/scoring-card]])。这一步的反污染设计很关键:别让客户的"我们内容很好"带偏基线。

输出:基线评分报告(总分 + 各维度 + 最弱项 + 否决项)。

### 04 Brief 内容简报 ★人工 checkpoint 1

agent 搭好内容框架,但**留出"专家洞察槽位"给业务专家填**。框架里明确标 `[业务专家填写洞察槽位]`,放最该有一手经验和真实数据的地方。

**硬约束:绝不用 AI 内容自动补这个槽位。** GEO 天生惩罚没有真实洞察的水文,这个 checkpoint 是把"人不可被绕过"做成流程硬门。模板见 [[../templates/content-brief]]。

输出:内容简报,状态为 `draft` 或 `ready-for-production`。

### 05 Build 生产

只有 brief 状态是 `ready-for-production` 才执行,否则硬拒。

- 写稿/改写,套用 GEO 改写方法(按排名档位和内容域分流,见 [[../methodology/geo-methods]])
- 生成 TDK(title/description/keywords)
- 生成 JSON-LD schema(用 `gen_schema.py`)
- 默认组合:流畅度 + 加统计,需要时叠标注来源
- **所有引语/统计/引用只用真实素材,素材不足产出待补清单**

输出:优化后内容 + TDK + schema,模板见 [[../templates/geo-content-spec]]。

### 06 Optimize 优化

- 页面级 on-page 审计(标题层级、可抽取性、定义块、答案前置)
- 技术审计(SSR 可见性、canonical、移动、速度)
- 内链优化、旧文刷新

输出:优化项清单 + 修复建议(带 severity 分级)。

### 07 QualityGate 质量门 ★人工 checkpoint 2

跑两道关:

1. **评分卡复评:** `geo_score.py` 重打分,对比基线,看提升幅度。
2. **GEU 护栏:** 改写后内容 KPC 矛盾度、Faithfulness Precision 是否守住。超阈值回退。

三态裁决:**SHIP**(无致命问题,放行)/ **FIX**(有问题但不致命,回 05/06 修)/ **BLOCK**(2+ 否决项或事实造假,人工介入)。**BLOCK 不可被自动绕过。**

输出:质量门报告 + 裁决。

### 08 Distribute 分发

按渠道矩阵给发布建议(见 [[../knowledge/03-publishing-channels]]):一稿四态、国内押生态、海外押 Reddit、知乎优先。产出针对本项目目标引擎的发布优先级清单。

输出:发布计划,模板见 [[../templates/publishing-plan]]。

### 09 WebSpec 网页规范

如果客户要建/改官网页面,给代码级网页架构建议(见 [[../knowledge/04-webpage-architecture]]):语义 HTML 骨架、按页面类型的 schema、SSR 要求、robots.txt(用 `gen_robots.py`)、llms.txt(用 `gen_llms_txt.py`)、国内 ICP/百度/字体本地化要点。

输出:网页规范文档,模板见 [[../templates/webpage-spec]]。

### 10 Re-audit 复审

发布满 7 天后回看:目标 AI 回答里有没有开始引用、引用占了多少、排名档位变化。结果反哺 02 调研,形成闭环。

输出:复审报告 + 下一轮优化方向。

---

## 两个 checkpoint 的产品意义

**Brief 阶段的洞察槽位和 QualityGate 的 BLOCK 裁决,是 HeiGe-GEO-SEO 区别于"工具说了算"的云端 SaaS 的核心。** GEO 不能全自动化:大模型搜索引擎主动惩罚 AI 拼的水文,必须有真实业务洞察才会被引用。所以这工具的定位是协作式 AI 员工,人守关键判断,AI 干承接的活。

---

## 相关

- 选引擎和市场 → [[../knowledge/01-llm-landscape]] · [[../knowledge/02-crawler-logic]]
- 改写和评分 → [[../methodology/geo-methods]] · [[../methodology/scoring-card]]
- 发布和建站 → [[../knowledge/03-publishing-channels]] · [[../knowledge/04-webpage-architecture]]
