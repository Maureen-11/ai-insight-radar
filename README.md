# AI Insight Radar

> AI market intelligence and model-evaluation workbench with traceable public evidence and human review.

[中文](#中文说明) · [English](#english)

**在线预览 / Live demo:** [https://maureen-11.github.io/ai-insight-radar/](https://maureen-11.github.io/ai-insight-radar/)

## 中文说明

面向面试展示、也可实际操作的「AI 行业情报与模型评测平台」。它的重点不是堆新闻，而是清楚展示一条研究判断如何从公开信号进入人工复核，并落到可执行行动。公开端仍是无密钥静态网站；审核后台只在本机运行。

## 运行

无需 Node 构建或 API Key。在项目根目录运行：

```powershell
python -m http.server 4173
```

打开 `http://127.0.0.1:4173/`。不要直接双击 HTML 文件，否则浏览器会拦截读取本地 JSON。

### 在线预览

GitHub Pages 部署完成后，可直接访问：[AI Insight Radar 在线预览](https://maureen-11.github.io/ai-insight-radar/)。若首次部署尚未完成，请等待 GitHub Actions 的 `Deploy GitHub Pages` 工作流显示成功。

## v0.5–v0.7：从静态展示到研究闭环

- **v0.5 研究后台**：FastAPI + SQLite 导入 876 条公开待办，结合来源可信度、时效、关键词、字段完整度和重复度排序；支持忽略、待验证、通过、退回，以及结论、影响、行动和证据编辑。
- **v0.6 评测闭环**：15 条 DeepSeek 真实输出进入人工抽检队列；事实性、完整性、引用正确性、结构化可用性与 Badcase 类型和自动指标分开保存。Promptfoo 配置用于声明式回归，不复制其源码。
- **v0.7 情报管线**：定时采集 RSS/Atom、监控官方页面内容哈希、记录来源健康度，生成已审核周报、厂商时间线和 RSS。自动化只生成待处理材料，不自动发布研究判断。
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

`data/signals.json` 是展示层的数据契约。每个 `Signal` 至少包含：

```json
{
  "id": "signal-001",
  "category": "模型",
  "title": "可追溯的标题",
  "conclusion": "研究结论",
  "whyNow": "为什么现在重要",
  "impact": ["具体影响"],
  "action": ["下一步行动"],
  "entities": ["相关实体"],
  "source": {"name": "来源", "url": "https://example.com", "publishedAt": "YYYY-MM-DD", "type": "厂商官方"},
  "evidence": [{"label": "证据", "url": "https://example.com", "note": "必要短说明"}],
  "confidence": 0.78,
  "priority": "high",
  "status": "待验证",
  "reviewed": true
}
```

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

`.github/workflows/research-pipeline.yml` 每天北京时间 08:00 运行，也可手动触发。它把待审核材料上传为 30 天有效的 Actions Artifact，而不是直接写回 `main` 或发布结论；这条人工闸门是有意保留的。

## 真实 DeepSeek 评测

评测页不会再展示伪造的静态分数。它使用 30 道公开合成题，对 DeepSeek 的三组模型/思考配置比较质量、引用命中、JSON 合法率、延迟、token 与成本。页面会明确说明：质量是关键词、引用编号和必填字段的规则加权信号；人工事实性、完整性与引用正确性复核完成前，不能把它当作生产结论。

```powershell
$env:DEEPSEEK_API_KEY = "仅在你自己的终端粘贴 Key"
python scripts/run_deepseek_eval.py --live --budget-cny 20
```

Key 只存在于当前终端会话，不会写入仓库。没有 `--live` 时脚本只运行零费用 mock 流程；mock 结果不会在页面中伪装为真实指标。`data/eval-review-template.json` 是真实运行后的人工抽样复核模板。

真实运行前，脚本会打印按配置价格、输入 token 估算和输出上限计算的最坏情况费用预估；预估超过传入预算时会拒绝发起请求。

## v0.4 模型能力地图

`模型能力地图`把模型信息拆成两类不可混排的证据：

- **本地实测**：本项目已运行的 DeepSeek 配置，才展示质量信号、引用命中、JSON 合法率、P50/P95、成本和失败率。
- **官方资料**：国内外厂商的可点击官方说明，只用于能力定位与后续候选池；未在本项目同题集复测时不显示效果分数。

档案在 `data/models.json`，证据在 `data/model-evidence.json`，人工抽检模板在 `data/model-review.json`。场景对比页将明确展示题集覆盖范围，不把总分伪装成单场景分数。

当前人工抽检队列仍标为**待复核**：在完成事实性、完整性、引用正确性与结构化可用性检查前，页面不会把规则指标写成最终的人类体验结论。

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

AI Insight Radar is an interview-ready AI market-intelligence and model-evaluation workbench. A local FastAPI/SQLite review desk handles private work-in-progress, while GitHub Pages publishes only reviewed, redacted data.

### Read this project in English

Start here:

1. **Signal stream** — each reviewed signal states a conclusion, its concrete impact, the recommended next action, and the source link.
2. **Signal detail** — open `signal.html?id=signal-001` to see why it matters now, evidence, open questions, confidence, priority, and review status.
3. **Weekly report** — generated from reviewed signals; every judgement links back to a dated public source.
4. **Model evaluation** — a clearly labelled local demo of comparing quality, latency, and cost on the same scenario. It is not an official benchmark result.
5. **Capability map** — filter domestic/overseas profiles and keep locally measured evidence separate from linked official information.
6. **Local review desk** — rank, edit, approve, return, or ignore incoming public signals before exporting them.

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

The scheduled GitHub Actions pipeline collects public metadata, detects official-page hash changes, produces a reviewed-only report preview, and uploads a manual-review artifact. It intentionally does not commit automated judgements to `main`.

### Model capability map

The capability map keeps two evidence layers separate: **local measurements** show only results truly run by this project, while **official information** is a linked capability profile for models not yet evaluated on the same task set. Public material never receives invented quality, latency, or cost scores.

`data/models.json`, `data/model-evidence.json`, and the local review database contain the model profiles, evidence records, and human-review queue. EvalScope (Apache-2.0) is an optional standard evaluation/performance backend; Promptfoo (MIT) is configured as an optional regression layer. Neither project source nor UI is copied into this repository.

The current human review queue is explicitly marked **pending**. Until factuality, completeness, citation correctness, and structured-output usability have been sampled by a reviewer, rule-based metrics are not presented as final human experience conclusions.

### Public-source workflow

```text
Public feeds and official-page changes
  → ignored work/ inbox and page-change files
  → SQLite ranking, human fact check, and research judgement
  → data/signals.json (reviewed and redacted only)
  → dated report, vendor timeline, and RSS
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
