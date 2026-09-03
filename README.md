# AI Insight Radar

> AI market intelligence and model-evaluation workbench with traceable public evidence and human review.

[中文](#中文说明) · [English](#english)

**在线预览 / Live demo:** [https://maureen-11.github.io/ai-insight-radar/](https://maureen-11.github.io/ai-insight-radar/)

## 中文说明

面向面试展示、也可实际操作的「AI 行业情报与模型评测平台」。它的重点不是堆新闻，而是展示一条判断如何由公开信号、具体证据和适用边界形成，并经人工确认落到可验证行动。公开端仍是无密钥静态网站；审核后台只在本机运行。

## v1.0：三层内容与证据标准

```text
每日公开来源采集
  → AI 待复核信号（选题线索，不是研究结论）
  → 深度研究草稿（事实、推理、反例、局限、行动）
  → 项目负责人人工确认
  → 正式研究档案与策略周报
```

- **待复核信号**：由自动管线生成，固定保留 `humanReviewed: false`，只能作为研究入口。
- **深度研究报告**：每篇 600–1000 个中文字符，至少两个具体来源且至少一个一手来源；事实通过 `[E1]` 等编号映射到证据。
- **正式策略周报**：只汇总已完成人工确认的深度报告。自动周报与正式周报状态分开。

当前五篇 v1.0 报告覆盖三篇模型评测/产品体验研究和两篇市场/竞品研究。重写后的草稿已撤销旧版“已复核”状态；只有在项目负责人逐条核对来源、推理、反例和限制后，才允许恢复公开发布。

## 运行

无需 Node 构建或 API Key。在项目根目录运行：

```powershell
python -m http.server 4173
```

打开 `http://127.0.0.1:4173/`。不要直接双击 HTML 文件，否则浏览器会拦截读取本地 JSON。

### 在线预览

GitHub Pages 部署完成后，可直接访问：[AI Insight Radar 在线预览](https://maureen-11.github.io/ai-insight-radar/)。若首次部署尚未完成，请等待 GitHub Actions 的 `Deploy GitHub Pages` 工作流显示成功。

## v0.5–v0.8：从静态展示到研究闭环

- **v0.5 研究后台**：FastAPI + SQLite 导入 876 条公开待办，结合来源可信度、时效、关键词、字段完整度和重复度排序；支持忽略、待验证、通过、退回，以及结论、影响、行动和证据编辑。
- **v0.6 评测闭环**：15 条 DeepSeek 真实输出进入人工抽检队列；事实性、完整性、引用正确性、结构化可用性与 Badcase 类型和自动指标分开保存。Promptfoo 配置用于声明式回归，不复制其源码。
- **v0.7 情报管线**：定时采集 RSS/Atom、监控官方页面内容哈希、记录来源健康度，生成已审核周报、厂商时间线和 RSS。自动化只生成待处理材料，不自动发布研究判断。
- **v0.8 人机双重验证**：15 条 DeepSeek 分层样本先由透明规则完成 AI 初评，再由项目负责人逐条确认最终分数；公开端只展示覆盖率、一致性与 Badcase 汇总，不公开原始回答。
- 公开站仍提供结论—影响—行动卡片、情报详情、模型能力地图和证据链接；本地实测与公开资料不混排。

## 本地研究后台（v0.5）

首次安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-backend.txt
```

启动：

```powershell
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 4180
```

打开 `http://127.0.0.1:4180/admin`。后台会初始化本机 `work/research.db`，可在队列中编辑并改变状态。只有字段完整且通过审核的条目才能发布；点击“导出公开数据”后才会更新 `data/signals.json`、周报、厂商时间线和 RSS。

`work/`、SQLite、原始响应和处理日志均被 Git 忽略。后台不提供公网认证，因此**不要把 4180 端口暴露到公网**。

## 数据与人工复核流程

```text
公开 RSS / Atom / 官方页面变化
  → work/inbox.json + work/page-changes.json（本机或 Actions 待办）
  → SQLite 排序、人工核对事实、编辑结论 / 影响 / 行动
  → data/signals.json（仅已审核、脱敏的公开数据）
  → 周报 / 厂商时间线 / feed.xml
```

`data/signals.json` 使用 v1.0 深度报告契约，可保存待确认草稿；公开首页、正式周报和 RSS 只渲染其中同时满足 `reviewed: true` 与 `review.humanReviewed: true` 的记录。核心字段包括：

```json
{
  "id": "signal-001",
  "schemaVersion": "1.0.0",
  "track": "模型评测与产品体验",
  "title": "可追溯的标题",
  "researchQuestion": "本报告要回答的问题",
  "executiveSummary": "首页使用的简短判断",
  "conclusion": "研究结论",
  "whyNow": "为什么现在重要",
  "observations": [{"id": "O1", "text": "来源直接支持的事实", "evidenceIds": ["E1"]}],
  "analysis": [{"id": "A1", "text": "本项目的比较与推理", "evidenceIds": ["E1", "E2"]}],
  "counterEvidence": [{"id": "C1", "text": "反例或削弱结论的证据", "evidenceIds": ["E2"]}],
  "limitations": ["适用范围和数据缺口"],
  "decisionImpact": [{"audience": "产品", "impact": "对决策的影响"}],
  "recommendedActions": [{"action": "验证动作", "ownerRole": "负责人角色", "metric": "指标", "expectedOutcome": "预期结果"}],
  "impact": ["具体影响"],
  "action": ["下一步行动"],
  "source": {"name": "来源", "url": "https://example.com", "publishedAt": "YYYY-MM-DD", "type": "厂商官方"},
  "evidence": [{"id": "E1", "title": "具体文档标题", "url": "https://example.com/doc", "publishedAt": "YYYY-MM-DD", "accessedAt": "YYYY-MM-DD", "sourceType": "厂商官方", "verified": true}],
  "confidence": {"overall": 0.78, "sourceQuality": 0.85, "evidenceAgreement": 0.75, "scopeFitness": 0.65, "rationale": "评分理由"},
  "reviewed": false,
  "review": {"aiDrafted": true, "humanReviewed": false, "reviewedAt": null, "version": "1.0-draft"}
}
```

发布门禁会检查正文深度、证据数量、一手来源、日期、链接、事实—证据映射、置信度理由和人工确认。任何一项缺失都不能进入正式档案。

## 采集公开来源

配置在 `data/sources.json`，仅包含不需要账号或 API Key 的公开源。运行：

```powershell
python scripts/collect_public_sources.py
python scripts/monitor_public_pages.py
python scripts/generate_publication.py
```

脚本会：

- 只保存公开标题、日期、URL 与最多 280 字的纯文本短摘要；不保存完整第三方文章。
- 按 URL 和稳定哈希去重，输出到本机忽略目录 `work/inbox.json`。
- 为待复核条目填入规则模板式的结论、影响、行动草稿，但**不会自动发布判断**。
- 官方更新页只保存内容哈希、变化摘要和必要元数据；本机快照在 `work/`，公开端只显示 `data/source-health.json`。
- 即使网络超时、XML 异常或一个来源失败，也保留已有数据并记录失败来源。

`.github/workflows/research-pipeline.yml` 每天北京时间 08:00 运行，也可手动触发。待审核原始材料保存为 30 天有效的 Actions Artifact；只有经过字段校验的公开安全汇总会由机器人提交到 `main`。

## v0.9 每日 AI 待复核信号

首页采用分层展示：`data/auto-brief.json` 是 DeepSeek 自动整理、未经人工复核的每日信号；它可以公开显示为选题线索，但不能进入人工研究档案或正式周报。`data/signals.json` 可包含带明确状态的草稿，但只有完成人工确认的报告才会被正式档案、周报和 RSS 渲染。

定时任务每天北京时间 08:00 采集 RSS、Atom 和官方页面变化，按日期去重后最多分析 10 条；每日预算硬上限为 ¥1。输出使用严格 JSON 契约，来源名称、URL 和发布日期始终由采集器写入，模型不能改写证据字段。原始文章、API 原始响应和模型思考过程都不会提交。

自动发布需要在 GitHub 仓库配置一次 Secret：

```text
Settings → Secrets and variables → Actions → New repository secret
Name: DEEPSEEK_API_KEY
```

只在 GitHub 的加密输入框粘贴 Key，不要写进代码、Issue 或聊天。缺少 Secret、输出校验失败或所有调用失败时，工作流不会覆盖上一份成功简报。`data/automation-status.json` 区分最近检查时间、最近成功时间和来源实际发布日期；没有新内容时显示“今日已检查，暂无有效更新”。

本地可用 mock 零费用验证完整管线：

```powershell
python scripts/collect_public_sources.py
python scripts/monitor_public_pages.py
python scripts/generate_auto_brief.py
```

## 真实 DeepSeek 评测

评测页不会再展示伪造的静态分数。它使用 30 道公开合成题，对 DeepSeek 的三组模型/思考配置比较质量、引用命中、JSON 合法率、延迟、token 与成本。页面会明确说明：质量是关键词、引用编号和必填字段的规则加权信号；人工事实性、完整性与引用正确性复核完成前，不能把它当作生产结论。

```powershell
$env:DEEPSEEK_API_KEY = "仅在你自己的终端粘贴 Key"
python scripts/run_deepseek_eval.py --live --budget-cny 20
```

Key 只存在于当前终端会话，不会写入仓库。没有 `--live` 时脚本只运行零费用 mock 流程；mock 结果不会在页面中伪装为真实指标。`data/eval-review-template.json` 是真实运行后的人工抽样复核模板。

### AI 初评 + 人工确认

本项目将 **AI 初评** 和 **人工最终确认** 分开保存，不能互相替代：AI 初评只按公开合成材料中的关键词、引用编号和字段映射给出可解释的规则信号；人工层确认或修改最终评分。当前公开汇总为 `data/eval-dual-review-summary.json`，覆盖三组配置各 5 条、共 15 条分层样本。

本次 15 条最终分数由项目负责人在对话中明确确认，结论是：这组抽样**未显示三种配置有明显体验差异**；主要 Badcase 为总结覆盖不足、条件遗漏和结构化字段映射错误。这不是多评审盲测，也不是官方模型榜单。公开页面不含原始模型回答；本机后台才可查看摘录。

如需在新的本地数据库中重建这次已确认的汇总，运行：

```powershell
python scripts/confirm_dual_evaluation.py
python scripts/generate_publication.py
```

真实运行前，脚本会打印按配置价格、输入 token 估算和输出上限计算的最坏情况费用预估；预估超过传入预算时会拒绝发起请求。

## v0.4 模型能力地图

`模型能力地图`把模型信息拆成两类不可混排的证据：

- **本地实测**：本项目已运行的 DeepSeek 配置，才展示质量信号、引用命中、JSON 合法率、P50/P95、成本和失败率。
- **官方资料**：国内外厂商的可点击官方说明，只用于能力定位与后续候选池；未在本项目同题集复测时不显示效果分数。

档案在 `data/models.json`，证据在 `data/model-evidence.json`，人工抽检模板在 `data/model-review.json`。场景对比页将明确展示题集覆盖范围，不把总分伪装成单场景分数。

公开页显示的双重验证状态以 `data/eval-dual-review-summary.json` 为准。即使已完成当前 15 条确认，新增题集、Prompt 或模型配置后也必须重新完成对应抽样，不能沿用本次结论。

EvalScope 是可选的 Apache-2.0 标准评测/性能后端；Promptfoo 是 MIT 许可的声明式回归工具。本仓库只提供 `evals/promptfooconfig.yaml`、Python provider 和确定性断言，没有复制二者源码或 UI。

Promptfoo 会真实调用模型并产生费用，因此默认不安装、不运行。准备好本机 Key 并确认预算后才执行：

```powershell
npx promptfoo@latest eval -c evals/promptfooconfig.yaml
```

每次实验记录题集版本、Prompt 版本、模型配置和运行时间。人工复核仍须在本地后台完成；系统不会把规则分数冒充人工体验结论。

运行离线测试：

```powershell
python -m unittest discover -s tests -p "test_*.py"
node --check app.js
node --check signal-detail.js
```

## 边界与第三方关系

- 本仓库中的界面、静态数据结构、采集脚本和规则模板为本项目新增代码，采用 [MIT License](LICENSE)。
- 项目没有复制 EvalScope、OpenCompass 或任何新闻站点的代码、文章全文或私有数据。
- [EvalScope](https://github.com/modelscope/evalscope)（Apache-2.0）是可选评测后端，[Promptfoo](https://github.com/promptfoo/promptfoo)（MIT）是可选回归工具，[OpenCompass](https://github.com/open-compass/opencompass)（Apache-2.0）仅作大型公开基准参考。
- [TrendRadar](https://github.com/sansan0/TrendRadar) 的调度、去重和报告流程以及 [Rival](https://github.com/webdog/rival) 的页面变化监控提供了设计参考；没有复制其源码。尤其 TrendRadar 为 GPL-3.0，不作为本 MIT 仓库的代码依赖。
- 示例来源均为公开链接。`signals.json` 的判断是面试 Demo 中经过人工整理的研究样例，应在正式使用前按链接、日期和原始资料复核。
- 不提交 API Key、Token、真实访谈原文或未经授权的数据。

---

## English

### What this is

AI Insight Radar is an evidence-driven AI market-intelligence and model-evaluation workbench. GitHub Pages separates automated candidate signals, deep research drafts, and human-confirmed reports; a local FastAPI/SQLite desk handles work in progress.

### v1.0 research standard

The publication flow is: public source → AI-generated candidate signal → deep research draft → project-owner verification → formal report and weekly strategy brief. Candidate signals never inherit a reviewed status. A deep report must contain 600–1,000 Chinese characters, at least two concrete sources including one first-party source, claim-to-evidence IDs, counterevidence, limitations, decision impact, testable actions, and an explainable confidence breakdown.

The five retained report IDs (`signal-001` through `signal-005`) are currently v1.0 drafts: three cover model evaluation/product experience and two cover market/competitive research. Their former reviewed flags were removed pending a fresh human source and reasoning check.

### Read this project in English

Start here:

1. **Candidate signal feed** — up to ten automatically generated items with source dates and links, always labelled as unreviewed research leads.
2. **Research archive** — only human-confirmed reports appear here, with evidence, impact, actions, and explicit boundaries.
3. **Report detail** — open `signal.html?id=signal-001` to inspect confirmed facts, evidence mapping, analysis, counterevidence, limitations, confidence rationale, and review status.
4. **Weekly report** — the formal section cites only human-confirmed deep reports; the automated seven-day observation remains separate.
5. **Model evaluation** — a clearly labelled local comparison of quality, latency, and cost on the same scenario. It is not an official benchmark result.
6. **Capability map** — filter domestic/overseas profiles and keep locally measured evidence separate from linked official information.
7. **Local review desk** — rank, edit, approve, return, or ignore incoming public signals before exporting them.

### Quick start

No Node build or API key is required.

```powershell
python -m http.server 4173
```

Open `http://127.0.0.1:4173/`. Use an HTTP server instead of opening the HTML file directly, because browsers block local JSON requests.

### Live demo

After the GitHub Pages deployment completes, open [AI Insight Radar live demo](https://maureen-11.github.io/ai-insight-radar/). On a first deployment, wait until the `Deploy GitHub Pages` GitHub Actions workflow succeeds.

### Real DeepSeek evaluation

The evaluation UI intentionally shows no synthetic scores. It displays results only after a real local run over 30 public synthetic cases and three DeepSeek configurations. The displayed “quality” figure is a deterministic signal based on expected keywords, citation IDs, and required fields; it is not a human quality score or an official benchmark.

```powershell
$env:DEEPSEEK_API_KEY = "paste-your-key-in-your-own-terminal"
python scripts/run_deepseek_eval.py --live --budget-cny 20
```

The key is read from the current terminal session only and is never written to this repository. Without `--live`, the script runs a zero-cost mock pipeline for testing; mock results are never presented as real results in the UI. `requirements-eval.txt` documents the optional EvalScope backend for additional benchmark and performance extensions.

Before a live run, the script prints a conservative cost estimate based on the price snapshot and configured token ceilings. It refuses to send requests when that estimate exceeds the supplied budget.

### Local review desk and automation

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-backend.txt
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 4180
```

Open `http://127.0.0.1:4180/admin`. The local database, inbox, page snapshots, model responses, and logs stay under ignored `work/` paths. Do not expose this unauthenticated local admin server to the internet.

The scheduled GitHub Actions pipeline runs at 08:00 China Standard Time. It collects public metadata, detects official-page hash changes, asks DeepSeek for a strict structured analysis, validates the result, and commits only the public-safe daily brief, rolling 14-day history, weekly observation, automation status, and source health files. The daily limit is ten items and CNY 1.

Add `DEEPSEEK_API_KEY` once under **Settings → Secrets and variables → Actions**. Never place the key in source code, an issue, or chat. Missing credentials, invalid output, or a total analysis failure leaves the last successful public brief untouched. Raw responses and reasoning are never committed.

### Model capability map

The capability map keeps two evidence layers separate: **local measurements** show only results truly run by this project, while **official information** is a linked capability profile for models not yet evaluated on the same task set. Public material never receives invented quality, latency, or cost scores.

`data/models.json`, `data/model-evidence.json`, and the local review database contain the model profiles, evidence records, and human-review queue. EvalScope (Apache-2.0) is an optional standard evaluation/performance backend; Promptfoo (MIT) is configured as an optional regression layer. Neither project source nor UI is copied into this repository.

The current 15-sample evaluation records AI initial scoring and project-owner confirmation separately. This is not a multi-rater blind study, and the sampled results do not support claiming that one configuration is clearly stronger.

### Public-source workflow

```text
Public feeds and official-page changes
  → AI candidate signals (automated, explicitly unreviewed)
  → deep research draft in the local desk
  → source, reasoning, counterevidence, and limitation check by the project owner
  → formal reviewed archive and weekly report
```

Run the manual collector with:

```powershell
python scripts/collect_public_sources.py
```

It uses no credentials or cloud model. It stores only public metadata (title, date, URL, and a short plain-text summary), deduplicates by URL/hash, and never promotes an item to a displayed signal automatically.

### Scope and data policy

- The UI, static data contract, collector, and rule templates are original project code under the [MIT License](LICENSE).
- EvalScope and OpenCompass are planned integration paths, not copied dependencies in this repository.
- Sample model results are local demo records. The interview page is a simulated input template, not a real expert interview.
- Do not commit API keys, tokens, private data, full third-party articles, or unapproved interview transcripts.

### Why there is no package

This repository is a static site, not an installable SDK or library. Therefore it intentionally has no GitHub Package. The published release marks a portfolio version of the research workbench, not a package distribution.
