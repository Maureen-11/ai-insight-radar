# AI Insight Radar

> AI market intelligence and model-evaluation workbench with traceable public evidence and human review.

[中文](#中文说明) · [English](#english)

**在线预览 / Live demo:** [https://maureen-11.github.io/ai-insight-radar/](https://maureen-11.github.io/ai-insight-radar/)

## 中文说明

面向面试展示的「AI 行业情报与模型评测平台」静态 Demo。它的重点不是堆新闻，而是清楚展示一条研究判断如何从公开信号进入人工复核，并落到可执行行动。

## 运行

无需 Node 构建或 API Key。在项目根目录运行：

```powershell
python -m http.server 4173
```

打开 `http://127.0.0.1:4173/`。不要直接双击 HTML 文件，否则浏览器会拦截读取本地 JSON。

### 在线预览

GitHub Pages 部署完成后，可直接访问：[AI Insight Radar 在线预览](https://maureen-11.github.io/ai-insight-radar/)。若首次部署尚未完成，请等待 GitHub Actions 的 `Deploy GitHub Pages` 工作流显示成功。

## v0.4.0：研究工作台与模型能力地图

- 情报列表默认展示：**结论、影响、建议行动**；来源是证据入口，不是装饰标签。
- `signal.html?id=signal-001` 提供独立详情：为什么重要、证据、待验证问题、人工复核、置信度和前后导航。
- 周报从 `data/signals.json` 中的已复核条目生成，每项都指向来源与日期。
- 重点厂商强调最新判断与建议动作，不使用没有解释力的装饰性分数。
- 模型能力地图可按**国内 / 海外**与**本地实测 / 官方资料**筛选；两类证据不混入同一排行榜。
- 模型评测页只展示本项目真实运行获得的 DeepSeek 本地记录；公开资料不填充效果、延迟或成本分数。
- 访谈页明确标为**模拟输入模板**；真实转写必须获得授权。

## 数据与人工复核流程

```text
公开 RSS / Atom 元数据
  → data/inbox.json（待复核）
  → 人工核对事实、补充结论 / 影响 / 行动
  → data/signals.json（正式展示）
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

配置在 `data/sources.json`，第一版仅包含不需要账号或 API Key 的公开 Atom/RSS 源。运行：

```powershell
python scripts/collect_public_sources.py
```

脚本会：

- 只保存公开标题、日期、URL 与最多 280 字的纯文本短摘要；不保存完整第三方文章。
- 按 URL 和稳定哈希去重，输出到 `data/inbox.json`。
- 为待复核条目填入规则模板式的结论、影响、行动草稿，但**不会自动发布判断**。
- 即使网络超时、XML 异常或一个来源失败，也保留已有收件箱，并写入 `data/collection-report.json`。

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

EvalScope 是可选的 Apache-2.0 标准评测/性能后端；Promptfoo 是后续 Agent/RAG 回归评测候选（MIT）。二者均未复制源码或 UI 到本仓库，也不会在默认流程中运行或发送数据。

运行离线测试：

```powershell
python -m unittest discover -s tests -p "test_*.py"
node --check app.js
node --check signal-detail.js
```

## 边界与第三方关系

- 本仓库中的界面、静态数据结构、采集脚本和规则模板为本项目新增代码，采用 [MIT License](LICENSE)。
- 项目没有复制 EvalScope、OpenCompass 或任何新闻站点的代码、文章全文或私有数据。
- EvalScope / OpenCompass 是后续可接入的开源评测后端；接入时应保留各自许可证与来源说明。
- 示例来源均为公开链接。`signals.json` 的判断是面试 Demo 中经过人工整理的研究样例，应在正式使用前按链接、日期和原始资料复核。
- 不提交 API Key、Token、真实访谈原文或未经授权的数据。

---

## English

### What this is

AI Insight Radar is a static, interview-ready workbench for AI market intelligence and model evaluation. It turns public signals into structured, reviewable research rather than presenting an untraceable news feed.

### Read this project in English

Start here:

1. **Signal stream** — each reviewed signal states a conclusion, its concrete impact, the recommended next action, and the source link.
2. **Signal detail** — open `signal.html?id=signal-001` to see why it matters now, evidence, open questions, confidence, priority, and review status.
3. **Weekly report** — generated from reviewed signals; every judgement links back to a dated public source.
4. **Model evaluation** — a clearly labelled local demo of comparing quality, latency, and cost on the same scenario. It is not an official benchmark result.
5. **Capability map** — filter domestic/overseas profiles and keep locally measured evidence separate from linked official information.

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

### Model capability map

The capability map keeps two evidence layers separate: **local measurements** show only results truly run by this project, while **official information** is a linked capability profile for models not yet evaluated on the same task set. Public material never receives invented quality, latency, or cost scores.

`data/models.json`, `data/model-evidence.json`, and `data/model-review.json` contain the model profiles, evidence records, and human-review queue. EvalScope (Apache-2.0) is the optional standard evaluation/performance backend; Promptfoo (MIT) is reserved for a future Agent/RAG regression layer. Neither project source nor UI is copied into this repository.

The current human review queue is explicitly marked **pending**. Until factuality, completeness, citation correctness, and structured-output usability have been sampled by a reviewer, rule-based metrics are not presented as final human experience conclusions.

### Public-source workflow

```text
Public RSS / Atom metadata
  → data/inbox.json (needs review)
  → human fact check and research judgement
  → data/signals.json (displayed, reviewed signals)
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
