# AI Insight Radar

面向面试展示的「AI 行业情报与模型评测平台」静态 Demo。它的重点不是堆新闻，而是清楚展示一条研究判断如何从公开信号进入人工复核，并落到可执行行动。

## 运行

无需 Node 构建或 API Key。在项目根目录运行：

```powershell
python -m http.server 4173
```

打开 `http://127.0.0.1:4173/`。不要直接双击 HTML 文件，否则浏览器会拦截读取本地 JSON。

## v0.2 的研究界面

- 情报列表默认展示：**结论、影响、建议行动**；来源是证据入口，不是装饰标签。
- `signal.html?id=signal-001` 提供独立详情：为什么重要、证据、待验证问题、人工复核、置信度和前后导航。
- 周报从 `data/signals.json` 中的已复核条目生成，每项都指向来源与日期。
- 重点厂商强调最新判断与建议动作，不使用没有解释力的装饰性分数。
- 模型评测页中的结果明确标为**本地演示记录**，不是官方成绩或真实生产结论。
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
