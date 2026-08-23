const signals = [
  { id: 1, category: "模型", marker: "M", markerClass: "marker-model", type: "模型动态", date: "今天 09:42", title: "模型 API 的比较维度，正在从参数规模转向“单位任务成本”", summary: "把价格、延迟、上下文窗口与业务成功率放在同一张表里，才能支持采购判断。", source: "公开厂商信息源", entity: "OpenAI · Anthropic", url: "https://openai.com/news/", score: 92 },
  { id: 2, category: "产品", marker: "P", markerClass: "marker-product", type: "产品动态", date: "昨天 17:20", title: "长上下文不再是卖点本身，检索与引用链成为体验分水岭", summary: "同一份文档在不同模型上的引用完整度，值得进入第一版场景评测集。", source: "Hugging Face Blog", entity: "RAG · Long Context", url: "https://huggingface.co/blog", score: 87 },
  { id: 3, category: "资本", marker: "C", markerClass: "marker-capital", type: "生态信号", date: "昨天 11:06", title: "开源模型生态继续向“可部署、可路由、可观测”扩展", summary: "单点模型能力之外，围绕部署与治理的工具层正在变成新的竞争入口。", source: "GitHub · ModelScope", entity: "Open Source AI", url: "https://github.com/modelscope/evalscope", score: 81 },
  { id: 4, category: "模型", marker: "M", markerClass: "marker-model", type: "模型动态", date: "08.22 15:48", title: "同一模型在通用测评与企业长尾问题上的排序可能完全不同", summary: "建议把错误类型、拒答质量和事实引用独立计分，保留低分样本用于复盘。", source: "EvalScope", entity: "评测方法", url: "https://github.com/modelscope/evalscope", score: 78 },
  { id: 5, category: "产品", marker: "P", markerClass: "marker-product", type: "应用动态", date: "08.22 10:12", title: "AI 产品的下一阶段竞争，转向能否嵌入现有工作流", summary: "从“聊天入口”走向“可审计的任务闭环”，需要同时考虑权限、成本和降级。", source: "Google AI Blog", entity: "AI Workflow", url: "https://blog.google/technology/ai/", score: 74 },
];

const vendors = [
  { name: "OpenAI", desc: "模型平台 · 工具调用", mark: "O", color: "#52778a", score: 94, delta: "+12%" },
  { name: "Anthropic", desc: "安全研究 · 长上下文", mark: "A", color: "#669b85", score: 88, delta: "+8%" },
  { name: "Google", desc: "多模态 · 基础设施", mark: "G", color: "#6e8eb4", score: 82, delta: "+4%" },
  { name: "DeepSeek", desc: "开源模型 · 推理", mark: "D", color: "#8a79a4", score: 77, delta: "+16%" },
];

const modelResults = {
  "知识库问答": [
    { name: "Qwen2.5-Max", provider: "Alibaba Cloud", mark: "Q", color: "#cf7656", quality: 91, citation: 94, latency: "1.42s", cost: "¥0.031", rec: "优先验证", recClass: "" },
    { name: "Claude 3.5 Sonnet", provider: "Anthropic", mark: "A", color: "#679a84", quality: 89, citation: 90, latency: "1.68s", cost: "¥0.047", rec: "备选", recClass: "alt" },
    { name: "GPT-4o mini", provider: "OpenAI", mark: "O", color: "#52788a", quality: 84, citation: 86, latency: "0.91s", cost: "¥0.012", rec: "成本优先", recClass: "neutral" },
  ],
  "长文档总结": [
    { name: "Claude 3.5 Sonnet", provider: "Anthropic", mark: "A", color: "#679a84", quality: 92, citation: 88, latency: "1.98s", cost: "¥0.052", rec: "优先验证", recClass: "" },
    { name: "Qwen2.5-Max", provider: "Alibaba Cloud", mark: "Q", color: "#cf7656", quality: 88, citation: 86, latency: "1.61s", cost: "¥0.035", rec: "备选", recClass: "alt" },
    { name: "GPT-4o mini", provider: "OpenAI", mark: "O", color: "#52788a", quality: 80, citation: 79, latency: "0.87s", cost: "¥0.014", rec: "成本优先", recClass: "neutral" },
  ],
  "结构化抽取": [
    { name: "GPT-4o mini", provider: "OpenAI", mark: "O", color: "#52788a", quality: 93, citation: 91, latency: "0.76s", cost: "¥0.011", rec: "优先验证", recClass: "" },
    { name: "Qwen2.5-Max", provider: "Alibaba Cloud", mark: "Q", color: "#cf7656", quality: 90, citation: 89, latency: "1.20s", cost: "¥0.029", rec: "备选", recClass: "alt" },
    { name: "Claude 3.5 Sonnet", provider: "Anthropic", mark: "A", color: "#679a84", quality: 86, citation: 87, latency: "1.35s", cost: "¥0.044", rec: "复杂任务", recClass: "neutral" },
  ],
};

const sources = [
  { name: "OpenAI Newsroom", type: "厂商官方", desc: "模型、API、产品与研究发布，作为一手动态来源。", url: "https://openai.com/news/", color: "#52788a" },
  { name: "Anthropic News", type: "厂商官方", desc: "模型能力、安全研究与产品更新。", url: "https://www.anthropic.com/news", color: "#679a84" },
  { name: "Google AI Blog", type: "厂商官方", desc: "多模态模型、基础设施和应用生态动态。", url: "https://blog.google/technology/ai/", color: "#6e8eb4" },
  { name: "Hugging Face Blog", type: "社区 / 论文", desc: "开源模型、数据集和生态工具的公开讨论。", url: "https://huggingface.co/blog", color: "#c87955" },
  { name: "ModelScope EvalScope", type: "评测工具", desc: "可扩展的大模型、VLM、AIGC 评测与报告。", url: "https://github.com/modelscope/evalscope", color: "#8a79a4" },
  { name: "DeepSeek GitHub", type: "开源项目", desc: "开源模型代码、权重和技术资料入口。", url: "https://github.com/deepseek-ai/DeepSeek-V3", color: "#5c8d78" },
];

const appState = { view: "dashboard", filter: "全部", search: "", scenario: "知识库问答", refreshedAt: "刚刚" };
const viewLabels = { dashboard: "情报雷达", eval: "模型评测", interview: "访谈纪要", report: "策略周报", sources: "信源管理", settings: "工作台设置" };

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));

function renderSignals() {
  const list = $("#signal-list");
  if (!list) return;
  const query = appState.search.trim().toLowerCase();
  const filtered = signals.filter((item) => {
    const matchesFilter = appState.filter === "全部" || item.category === appState.filter;
    const haystack = `${item.title} ${item.summary} ${item.source} ${item.entity}`.toLowerCase();
    return matchesFilter && (!query || haystack.includes(query));
  });
  list.innerHTML = filtered.length ? filtered.map((item) => `
    <article class="signal-item">
      <div class="signal-marker ${item.markerClass}">${escapeHtml(item.marker)}</div>
      <div class="signal-content">
        <div class="signal-topline"><span class="signal-type">${escapeHtml(item.type)}</span><span>·</span><span>${escapeHtml(item.date)}</span></div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.summary)}</p>
        <div class="signal-bottom"><a class="source-chip" href="${item.url}" target="_blank" rel="noreferrer">${escapeHtml(item.source)}</a><span class="signal-entity">${escapeHtml(item.entity)}</span></div>
      </div>
      <div class="signal-score"><div class="score-ring" style="--score:${item.score}"><span>${item.score}</span></div><span class="score-label">重要性</span></div>
    </article>`).join("") : `<div class="empty-state"><span>⌕</span><strong>没有匹配的信号</strong><p>换一个关键词或切换分类试试。</p></div>`;
}

function renderVendors() {
  const list = $("#vendor-list");
  if (!list) return;
  list.innerHTML = vendors.map((vendor) => `
    <div class="vendor-row"><span class="vendor-logo" style="background:${vendor.color}">${vendor.mark}</span><div class="vendor-info"><strong>${vendor.name}</strong><span>${vendor.desc}</span></div><div class="vendor-momentum"><b>${vendor.score}</b><span>${vendor.delta}</span></div><div class="vendor-bar"><span style="width:${vendor.score}%"></span></div></div>`).join("");
}

function renderEval() {
  const rows = modelResults[appState.scenario];
  const title = $("#eval-title");
  const body = $("#eval-table-body");
  if (!body || !title) return;
  title.textContent = `${appState.scenario} · 模型对比`;
  body.innerHTML = rows.map((row) => `<tr>
    <td><div class="model-cell"><span class="model-badge" style="background:${row.color}">${row.mark}</span><div class="model-name"><strong>${row.name}</strong><span>${row.provider}</span></div></div></td>
    <td><span class="quality-value">${row.quality}</span><span class="quality-bar-inline"><span style="width:${row.quality}%"></span></span></td>
    <td>${row.citation}%</td><td>${row.latency}</td><td>${row.cost}</td>
    <td><span class="recommend-badge ${row.recClass}">${row.rec}</span></td><td><button class="row-action" type="button" data-toast="已打开 ${row.name} 的样本明细">↗</button></td>
  </tr>`).join("");
  $$(".scenario-tab").forEach((tab) => tab.classList.toggle("is-selected", tab.dataset.scenario === appState.scenario));
}

function renderSources() {
  const catalog = $("#source-catalog");
  if (!catalog) return;
  catalog.innerHTML = sources.map((source) => `<article class="panel source-card"><span class="vendor-logo" style="background:${source.color}">${source.name.slice(0, 1)}</span><h2>${source.name}</h2><p>${source.desc}</p><span class="source-type">${source.type}</span><br /><a class="source-url" href="${source.url}" target="_blank" rel="noreferrer">打开公开来源 ↗</a></article>`).join("");
}

function setView(view) {
  if (!viewLabels[view]) return;
  appState.view = view;
  $$('[data-view-panel]').forEach((panel) => panel.classList.toggle("is-visible", panel.dataset.viewPanel === view));
  $$(".nav-item[data-view]").forEach((item) => item.classList.toggle("is-active", item.dataset.view === view));
  const label = $("#breadcrumb-label");
  if (label) label.textContent = viewLabels[view];
  window.scrollTo({ top: 0, behavior: "smooth" });
}

let toastTimer;
function showToast(message) {
  const toast = $("#toast");
  $("#toast-message").textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2500);
}

function exportReport() {
  const markdown = `# AI Insight Radar · AI 行业策略周报\n\n生成时间：2026.08.24（本地演示版）\n\n## 本周判断\n\n1. 从“谁的模型更强”转向“谁能把闭环交付”。\n2. 开源模型的机会在“可控”和“可改”，不只是免费。\n3. 情报团队的价值在“把变化翻译成动作”。\n\n## 建议下周动作\n\n用 30 条真实业务问题建立第一版“场景评测集”，再决定模型路由和产品集成优先级。\n\n## 证据来源\n\n- OpenAI Newsroom: https://openai.com/news/\n- Anthropic News: https://www.anthropic.com/news\n- Google AI Blog: https://blog.google/technology/ai/\n- Hugging Face Blog: https://huggingface.co/blog\n- DeepSeek GitHub: https://github.com/deepseek-ai/DeepSeek-V3\n\n> 说明：模型结果为演示数据，替换本地评测数据后再用于正式结论。`;
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = "ai-insight-radar-weekly-brief.md"; anchor.click();
  URL.revokeObjectURL(url);
  showToast("周报 Markdown 已下载");
}

function openTranscriptModal(open = true) {
  const modal = $("#transcript-modal");
  modal.classList.toggle("is-open", open);
  modal.setAttribute("aria-hidden", String(!open));
  if (open) setTimeout(() => $("#transcript-input").focus(), 50);
}

document.addEventListener("click", (event) => {
  const viewButton = event.target.closest("[data-view], [data-view-jump]");
  if (viewButton) { event.preventDefault(); setView(viewButton.dataset.view || viewButton.dataset.viewJump); return; }
  const filterButton = event.target.closest("[data-filter]");
  if (filterButton) { appState.filter = filterButton.dataset.filter; $$("#signal-filters .filter-pill").forEach((pill) => pill.classList.toggle("is-selected", pill === filterButton)); renderSignals(); return; }
  const scenarioButton = event.target.closest("[data-scenario]");
  if (scenarioButton) { appState.scenario = scenarioButton.dataset.scenario; renderEval(); return; }
  const toastButton = event.target.closest("[data-toast]");
  if (toastButton) { showToast(toastButton.dataset.toast); return; }
  if (event.target.closest("#refresh-data")) { appState.refreshedAt = "刚刚"; showToast("公开来源状态已刷新"); return; }
  if (event.target.closest("#export-report")) { exportReport(); return; }
  if (event.target.closest("#open-transcript")) { openTranscriptModal(true); return; }
  if (event.target.closest(".modal-close") || event.target.id === "transcript-modal") { openTranscriptModal(false); return; }
  if (event.target.closest("#apply-transcript")) {
    const text = $("#transcript-input").value.trim();
    if (!text) { showToast("请先粘贴一段已获授权的转写文本"); return; }
    openTranscriptModal(false); showToast("已生成本地结构化草稿"); return;
  }
});

$("#signal-search")?.addEventListener("input", (event) => { appState.search = event.target.value; renderSignals(); });
$("#global-search")?.addEventListener("input", (event) => {
  const value = event.target.value.trim();
  if (value && appState.view !== "dashboard") setView("dashboard");
  appState.search = value; $("#signal-search").value = value; renderSignals();
});
document.addEventListener("keydown", (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); $("#global-search").focus(); } if (event.key === "Escape") openTranscriptModal(false); });

renderSignals();
renderVendors();
renderEval();
renderSources();
