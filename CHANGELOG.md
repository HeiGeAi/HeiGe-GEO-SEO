# Changelog

## v1.1.0 (2026-06-21)

把工具从「诊断 + 知识」升级成「诊断 → 产出 → 度量」全链路,同时焊死中国优先护城河。基于对 20+ 成熟 GEO 产品的竞品深研(商业可见度监控 SaaS Profound/Otterly/Peec/Brandlight/Scrunch 等、内容优化工具 Surfer/Jasper/Writesonic/AutoGEO、技术审计 aeorank/geo-optimizer、国内透镜GEO/GEOBase 等)。

### 产出层(最强差异化)

- **改写指令编译器**(`rewrite`):吃打分结果,输出可喂任意 LLM 的精确改写指令包。每条含 GEO 方法、预期提升、精确改写指令、按目标引擎分叉、反 AI 味约束。LLM 无关,绕开商业工具把改写锁死在自家黑盒的封闭性。
- **GEO Content Brief 生成器**(`brief`):以可被引用性为骨架,区别于市面 SEO brief。
- **反 AI 味约束库**(`anti_ai`):把人机感做成显式约束子句,复用 HeiGe 写作硬规则,也能当检测器。

### 度量层(可解释离线版)

- **buyer prompt 集生成器**(`prompts`):意图问句,漏斗 × persona × 品牌/非品牌,非品牌优先,中英双语。
- **Share of Voice 度量**(`sov`):三公式(Mention/调和加权/Citation)+ 竞争位基准阈值 + 采样置信度 + 别名合并。
- **「为何没被引用」7 根因诊断**(`diagnose`):确定性清单,每条 pass/fail + 修复动作,含国内 ICP 备案检测。
- **GEO 归因检测**(`attribution`):GA4 渠道组正则(含国内引擎)+ UTM 规范 + 服务器日志 AI 爬虫 UA 解析。

### 文件 + 工程层

- **实体层 schema**:新增 Organization / Person / WebSite,强制 @id + sameAs(AI 引用前置门槛)。
- **9 文件家族**:补 ai.txt、robots.patch、sitemap.xml、answers.json、citations.json、humans.txt、feed.xml。
- **报告**:HTML 自包含报告 + SARIF(接 GitHub Code Scanning)。
- **批量站点审计**(`batch`):弱页优先排序。
- **WebMCP 就绪审计**(`agentready`):表单 agent 可调用性静态审计。

### 知识库增量

- 新增 `05-engine-differences.md`:引擎差异矩阵(各引擎检索机制 + 格式偏好 + 差异化战术)。
- 新增 `06-ai-visibility-measurement.md`:SoV 度量学 + prompt 测试方法 + 归因。
- `03-publishing-channels.md`:补国产引擎信源权重表(新榜 1683.6 万条实证)+ 平台依附 vs 域名主权 + 国产平台发布 SOP。

### 边界(刻意不做)

实时 AI 可见度监控(需常驻爬 9 引擎,违背零依赖)、自动内容改写引擎(交宿主 agent)、训练模型。度量学进 v1.1,采集寄生宿主 agent,联网监控留 v1.2。

### 测试

44 → 96 个单测全过,build/validate/案例全绿。

## v1.0.0 (2026-06-20)

首个版本。中国优先的 GEO + SEO 优化系统:四大知识库 + GEO 论文 9 方法与 6 维 22 项评分卡 + 零依赖脚本(打分器/robots/llms.txt/schema)+ 10 阶段工作流 + 单源转译 CC/Codex/OpenClaw/Hermes + 3 案例 + 44 单测 + CI。
