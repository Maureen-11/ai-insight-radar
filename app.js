const state = { signals: [], sources: [], evalResults: null, filter: "全部", query: "", view: "radar" };
const labels = { radar: "情报雷达", report: "策略周报", eval: "模型评测", interview: "访谈纪要", sources: "公开信源" };
const vendors = [
  { name: "OpenAI", trend: "观察维度上升", verdict: "模型能力、工具调用与价格变化要放在同一套采购表中。", action: "下次评测同时记录质量、延迟与成本。" },
  { name: "Anthropic", trend: "长文场景持续相关", verdict: "长上下文能力仍需用引用准确率和错误定位来验证。", action: "补充长文档引用题。" },
  { name: "Hugging Face", trend: "生态信号活跃", verdict: "开源模型与工具链是部署和评测方案的重要入口。", action: "关注版本变动并跑本地 fixture。" },
  { name: "ModelScope", trend: "评测工具可落地", verdict: "开源评测框架可以支撑可重复的业务场景比较。", action: "将场景题接入 EvalScope 验证。" }
];
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const priorityLabel = { high: "高优先级", medium: "中优先级", low: "低优先级" };
function displayRunTime(value) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? "时间待补充" : date.toLocaleString("zh-CN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Shanghai" }); }

function toast(message) { const el = $("#toast"); el.textContent = message; el.classList.add("is-visible"); window.setTimeout(() => el.classList.remove("is-visible"), 2600); }
function localDate(value) { const date = new Date(`${value}T00:00:00`); return Number.isNaN(date.valueOf()) ? "日期待补充" : date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" }); }
function reviewedSignals() { return state.signals.filter((item) => item.reviewed); }
function matches(signal) { const haystack = [signal.title, signal.conclusion, signal.category, ...(signal.entities || []), signal.source?.name].join(" ").toLowerCase(); return (state.filter === "全部" || signal.category === state.filter) && (!state.query || haystack.includes(state.query.toLowerCase())); }

function renderMetrics() {
  const reviewed = reviewedSignals(); const high = reviewed.filter((item) => item.priority === "high").length;
  $("#metrics").innerHTML = [[reviewed.length, "已复核情报"], [high, "高优先级判断"], [state.sources.length, "已配置公开信源"], [reviewed.filter((item) => item.status === "待验证").length, "需要验证的问题"]].map(([value, label]) => `<article class="metric"><strong>${value}</strong><span>${label}</span></article>`).join("");
  $("#pipeline-status").textContent = `${reviewed.length} 条已复核 · ${state.sources.length} 个公开源`;
}
function renderSignals() {
  const list = $("#signal-list"); const result = reviewedSignals().filter(matches);
  $("#signal-count").textContent = `${result.length} 条可读`;
  list.innerHTML = result.length ? result.map((item) => `<article class="signal">
    <div class="signal-top"><span class="tag ${item.priority}">${priorityLabel[item.priority] || "待定"}</span><span>${escapeHtml(item.category)}</span><span>·</span><span>${localDate(item.source?.publishedAt)}</span><span>·</span><span>${escapeHtml((item.entities || []).join(" / "))}</span></div>
    <h3><a href="signal.html?id=${encodeURIComponent(item.id)}">${escapeHtml(item.title)}</a></h3>
    <p class="signal-conclusion">结论：${escapeHtml(item.conclusion)}</p>
    <div class="signal-detail-row"><strong>影响</strong><span>${escapeHtml((item.impact || []).join("；"))}</span></div>
    <div class="signal-detail-row"><strong>建议行动</strong><span>${escapeHtml((item.action || []).join("；"))}</span></div>
    <div class="signal-footer"><a class="source-link" href="${escapeHtml(item.source?.url)}" target="_blank" rel="noreferrer">来源：${escapeHtml(item.source?.name || "来源待补充")} ↗</a><span>置信度 ${Math.round((item.confidence || 0) * 100)}%</span><span>状态：${escapeHtml(item.status || "待复核")}</span><a class="text-link" href="signal.html?id=${encodeURIComponent(item.id)}">完整研判 →</a></div>
  </article>`).join("") : '<div class="empty">没有匹配的已复核情报。请更换分类或搜索词。</div>';
}
function renderWeekly() {
  const top = reviewedSignals().sort((a, b) => (b.priority === "high") - (a.priority === "high") || b.confidence - a.confidence).slice(0, 3);
  $("#weekly-preview").innerHTML = top.map((item) => `<article><strong>${escapeHtml(item.conclusion)}</strong><span>${escapeHtml(item.source.name)} · ${localDate(item.source.publishedAt)}</span></article>`).join("");
  $("#report-judgements").innerHTML = top.map((item) => `<section class="judgement"><h3>${escapeHtml(item.conclusion)}</h3><p><strong>为什么现在：</strong>${escapeHtml(item.whyNow)}</p><p><strong>影响：</strong>${escapeHtml((item.impact || []).join("；"))}</p><div class="evidence">证据：<a href="${escapeHtml(item.source.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.source.name)} · ${localDate(item.source.publishedAt)} ↗</a> · 人工复核：${item.reviewed ? "是" : "否"}</div></section>`).join("");
  const actions = [...new Set(top.flatMap((item) => item.action || []))].slice(0, 5);
  $("#report-actions").innerHTML = actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>暂无行动项</li>";
}
function renderVendors() { $("#vendor-list").innerHTML = vendors.map((vendor) => `<article class="vendor"><div class="vendor-top"><strong>${vendor.name}</strong><span class="trend">${vendor.trend}</span></div><p>${vendor.verdict}</p><p class="action">建议：${vendor.action}</p></article>`).join(""); }
function renderSources() { $("#source-catalog").innerHTML = state.sources.length ? state.sources.map((source) => `<article class="panel source-card"><p class="eyebrow">${escapeHtml(source.type)}</p><h2>${escapeHtml(source.name)}</h2><p>分类：${escapeHtml(source.category)} · 实体：${escapeHtml((source.entities || []).join(" / "))}</p><a class="text-link" href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">打开公开来源 ↗</a></article>`).join("") : '<div class="empty">未能读取 sources.json。</div>'; }
function renderEvalFollowup(results) {
  const target = $("#eval-followup");
  if (!results || results.status !== "real") { target.innerHTML = ""; return; }
  const rows = results.configurations || []; const bestQuality = [...rows].sort((a, b) => b.quality - a.quality)[0]; const bestValue = [...rows].sort((a, b) => a.costCny - b.costCny)[0]; const slowest = [...rows].sort((a, b) => b.latencyMs.p95 - a.latencyMs.p95)[0];
  target.innerHTML = `<section class="panel eval-insight"><div class="panel-heading"><div><p class="eyebrow">本次运行的谨慎解读</p><h2>先做什么，再决定是否扩容</h2></div><span class="tag neutral">自动指标，待人工抽检</span></div><div class="insight-grid"><article><strong>质量信号最高</strong><p>${escapeHtml(bestQuality.label)} 在自动规则评分与引用命中上领先（${bestQuality.quality} / ${bestQuality.citationHitRate}%）；但这不等于人工事实性结论。</p></article><article><strong>成本最低</strong><p>${escapeHtml(bestValue.label)} 本次 30 题成本为 ¥${Number(bestValue.costCny).toFixed(4)}，可作为低成本基线配置。</p></article><article><strong>需要优先修复</strong><p>三组 JSON 合法率均偏低；先强化结构化输出约束与 schema 校验，再把结果用于业务流程。</p></article></div><div class="method-grid"><article><h3>指标口径</h3><p>“质量”是关键词命中、引用编号命中与必填字段的规则加权信号；不是人工主观评分，也不是官方榜单。</p></article><article><h3>实验边界</h3><p>30 道公开合成题、同一厂商 3 组配置。${escapeHtml(slowest.label)} 的 p95 为 ${slowest.latencyMs.p95} ms，不能据此推断其他场景或厂商。</p></article><article><h3>下一步</h3><p>按 <code>data/eval-review-template.json</code> 对每组 5 个样本人工评分；再补充结构化 JSON 指令后复跑同一题集。</p></article></div></section>`;
}
function renderEval() {
  const results = state.evalResults; const body = $("#eval-body");
  if (!results || results.status !== "real") { body.innerHTML = '<tr><td colspan="7" class="empty">尚未运行真实评测。运行脚本前，页面不会展示任何模拟分数。</td></tr>'; renderEvalFollowup(null); return; }
  $("#eval-notice").innerHTML = `<strong>真实运行 · ${escapeHtml(results.provider)}</strong><span>运行时间：${escapeHtml(displayRunTime(results.runAt))}（北京时间） · 实际成本：¥${Number(results.actualCostCny || 0).toFixed(4)} · 人工复核：${escapeHtml(results.humanReview || "pending")}</span>`;
  $("#eval-run-meta").textContent = `真实运行 · ${results.configurations.reduce((n, item) => n + item.samples, 0)} 次调用 · 题集 ${results.datasetVersion}`;
  $("#eval-review-state").textContent = results.humanReview === "complete" ? "人工复核已完成" : "人工复核待完成";
  body.innerHTML = results.configurations.map((row) => `<tr><td><strong>${escapeHtml(row.label)}</strong><br><small>${escapeHtml(row.model)} · ${escapeHtml(row.thinking)}</small></td><td>${row.quality}</td><td>${row.citationHitRate}%</td><td>${row.jsonValidRate}%</td><td>${row.latencyMs.p50} / ${row.latencyMs.p95} ms</td><td>¥${row.costCny}</td><td>${row.failureRate}%</td></tr>`).join("");
  renderEvalFollowup(results);
}
function renderAll() { renderMetrics(); renderSignals(); renderWeekly(); renderVendors(); renderSources(); renderEval(); }

function setView(view) {
  if (!labels[view]) return; state.view = view;
  $$('[id$="-view"]').forEach((panel) => panel.classList.toggle("is-visible", panel.id === `${view}-view`));
  $$("[data-view]").forEach((item) => item.classList.toggle("is-active", item.dataset.view === view));
  $("#crumb").textContent = labels[view];
  if (location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}
document.addEventListener("click", (event) => {
  const viewLink = event.target.closest("[data-view]"); if (viewLink) { event.preventDefault(); setView(viewLink.dataset.view); }
  const filter = event.target.closest("[data-filter]"); if (filter) { state.filter = filter.dataset.filter; $$("[data-filter]").forEach((button) => button.classList.toggle("is-selected", button === filter)); renderSignals(); }
});
$("#global-search").addEventListener("input", (event) => { state.query = event.target.value.trim(); if (state.view !== "radar") setView("radar"); renderSignals(); });
window.addEventListener("hashchange", () => setView(location.hash.slice(1) || "radar"));

async function boot() {
  try {
    const [signals, sources, evalResults] = await Promise.all([fetch("data/signals.json"), fetch("data/sources.json"), fetch("data/eval-results.json")]);
    if (!signals.ok || !sources.ok || !evalResults.ok) throw new Error("数据文件无法读取");
    state.signals = await signals.json(); state.sources = await sources.json(); state.evalResults = await evalResults.json();
    if (!Array.isArray(state.signals) || !Array.isArray(state.sources)) throw new Error("数据格式错误");
    renderAll(); setView(location.hash.slice(1) || "radar");
  } catch (error) {
    $("#pipeline-status").textContent = "本地数据加载失败";
    $("#signal-list").innerHTML = `<div class="empty">无法加载本地数据：${escapeHtml(error.message)}。请通过本地 HTTP 服务访问。</div>`;
    toast("数据加载失败，请检查本地服务");
  }
}
boot();
