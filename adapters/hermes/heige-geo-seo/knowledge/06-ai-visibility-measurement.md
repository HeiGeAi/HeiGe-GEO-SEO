# 知识库 06 · AI 可见度度量学

> v1.1 新增。怎么科学地量化"被 AI 引用"。这是 `prompts`、`sov`、`attribution` 三个脚本的方法学依据。**度量学 100% 离线,采集(真去问大模型)寄生宿主 agent 或人工。**

---

## 一句话判断

**成熟监控 SaaS(Profound/Otterly/Peec)卖的是持续爬 9 个引擎的大盘数据,数万刀/年。我方不拼数据规模,拼可解释、可复现、零依赖的度量学:脚本生成 prompt 集和打分逻辑,采集交给宿主 agent。** 拿到 90% 价值,绕开 100% 基建。

---

## 一、Prompt 级测试(GEO 版关键词覆盖)

`prompt coverage` = 多少相关 prompt 能让你的品牌出现。这是 GEO 的核心 KPI。

**方法学锚点(竞品实证):**

- **规模**:最小 50 条,推荐 100-200 条/引擎,可扩到 1000;每主题 20-30 条。
- **采样**:同一 prompt 在同一引擎重复跑 3-5 次取稳定性(LLM 非确定性,单次结果统计上不稳定)。
- **稳定阈值**:200 prompts × 5 引擎约 3000 输出才开始稳定。
- **分层**:漏斗 Awareness / Evaluation / Conversion / Post-Purchase 四段 × persona × 品牌词/非品牌词。**非品牌词优先于品牌词**(品牌词必中,信息量低)。
- **来源**:不是历史关键词排名,而是销售通话、客服工单、Reddit、客户访谈、Quora、Google PAA。

脚本:`geo_cli prompts --brand X --category Y --competitor Z --problem P --persona R` 生成结构化意图问句集(中英双语,非品牌优先)。真去问大模型交给宿主 agent,把回答回填给 `sov`。

---

## 二、Share of Voice 三套公式

| 公式 | 定义 | 用途 |
|---|---|---|
| **Mention SoV** | 你的品牌提及数 ÷ 所有被追踪品牌总提及数 × 100 | 最常用,相对可见度 |
| **Position-weighted SoV** | 调和衰减加权(位置1=1.0、位置2=0.50、位置3=0.33…即 1/n) | 加权后更稳,看被引用得早不早 |
| **Citation SoV** | 你的域名被引用数 ÷ 所有来源总引用数 × 100 | 数真实 URL 引用,不是文字提及 |

**度量学要点:**

- **开放分母**:统计所有出现的品牌,包括没列入的竞品。
- **分引擎分别报**:国内豆包/千问/元宝/文心/DeepSeek/Kimi 各算各的。
- **基线期 ≥4 周**再设目标,季度 re-baseline。
- **别名合并**:把"艾克米/Acme/ACME"合并成一个品牌(国内工具标配)。

**竞争位基准阈值表:**

| 竞争位 | Mention SoV 目标 | Weighted SoV 目标 |
|---|---|---|
| 领导者 | 40-70% | 35-60% |
| Top3 挑战者 | 20-35% | 15-30% |
| Top10 | 10-20% | 7-15% |
| 新进入者 | 2-10% | 1-7% |

脚本:`geo_cli sov --input records.json --brand X --competitor Y --brand-domain x.com` 三公式全算 + 自动判竞争位 + 标采样不稳定 prompt。

**国内口径对齐**:提及率 + SOV 声量占比 + 推荐排名三件套,验收标准是"可截图、可复核、可量化",拒绝模糊的"提升曝光"。

---

## 三、「为何没被引用」7 根因诊断

度量发现可见度低之后,用诊断器定位原因。7 条引用失败根因(确定性检查,`geo_cli diagnose`):

1. canonical 缺失或不规范
2. 实体命名跨位置不一致
3. 缺 Organization/Person 来源标注
4. 机器可读关系弱(无 sameAs)
5. 开头缺 40-60 词自包含答案块
6. 缺 FAQPage schema
7. 信息缺口(你没回答的问题 → AI 引竞品,需对照 prompt 覆盖率)

这是相对黑盒 SaaS 的可解释优势:每条 pass/fail + 具体修复动作。

---

## 四、GEO 归因检测

**AI 来源流量转化率高(实测最高 15.9% vs 自然流量 1.76%),但 35%-70% 的 AI 会话没有 referrer,掉进 GA4 的 Direct 黑洞。** 客户看不到 AI 带来的转化,就觉得 GEO 没 ROI。

两层归因:

- **Layer1 可观测 referral**:GA4 自定义渠道组正则(含国内引擎域名 doubao/yiyan/tongyi/yuanbao/kimi/deepseek),把 AI 流量从 Direct 捞出来。
- **Layer2 推断影响**:被引用页的 direct 流量抬升 + 品牌搜索增量 + CRM 来源捕获,靠时间相关性。

配套:UTM 命名规范(llms.txt/answers.json 出站链接统一打 `utm_source=llm`)+ 服务器日志 AI 爬虫 UA 解析。脚本:`geo_cli attribution --url x.com`(出物料)、`--log access.log`(解析日志)。

---

## 五、引用质量(v1.5,从"测覆盖"到"测质量管风险")

被引用得多不等于被引用得好。`sov` 现在多输出三层质量信号:

- **被引 sentiment**:同一次提及,是"首选推荐"还是"这家有争议不建议"。负面提及在纯 SoV 里和正面等价还因出现得早拿高分,会把负面误报成可见度。`sov` 的 `mention_sentiment` 拆 positive/neutral/negative。
- **earned vs owned 引用**:自有域名刷十次引用,抗波动远不如被十个第三方权威源引(82-94% 引用来自 earned media)。`citation_owned_earned` 报 earned 占比,越高越抗波动。
- **多轮留存**:用户问完"最好的 X"会追问"和 Y 比呢""有什么坑",品牌在首轮出现 vs 多轮被维持是两件事(run 管采样抖动,turn 管对话演进)。记录带 `turn` 字段,`sov` 出 `by_turn` 首轮命中 vs 后续留存。

配套工具:`factcheck`(品牌错误信息纠正,你提供真相→标 AI 说错的)、`lostprompt`(竞品替换分析,找竞品占位你缺席的 prompt→针对性夺回)。

## 边界(诚实说明)

**实时持续监控不做。** 那要常驻爬 9 个引擎、维护采集基建、处理反爬登录态,违背零依赖底线。度量学进 v1.1,采集这步交给宿主 agent 或人工触发,或留到 v1.2 接国产/海外模型 API。

---

## 相关

- 生成 prompt 集 → `geo_cli prompts`
- 算 SoV → `geo_cli sov`
- 诊断根因 → `geo_cli diagnose`
- 归因物料 → `geo_cli attribution`
- 分引擎差异 → [[05-engine-differences]]
