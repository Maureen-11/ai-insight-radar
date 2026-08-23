const state = { signals: [], sources: [], filter: "全部", query: "", view: "radar" };
const labels = { radar: "情报雷达", report: "策略周报", eval: "模型评测", interview: "访谈纪要", sources: "公开信源" };
const vendors = [
  { name: "OpenAI", trend: "观察维度上升", verdict: "模型能力、工具调用与价格变化要放在同一套采购表中。", action: "下次评测同时记录质量、延迟与成本。" },
  { name: "Anthropic", trend: "长文场景持续相关", verdict: "长上下文能力仍需用引用准确率和错误定位来验证。", action: "补充长文档引用题。" },
  { name: "Hugging Face", trend: "生态信号活跃", verdict: "开源模型与工具链是部署和评测方案的重要入口。", action: "关注版本变动并跑本地 fixture。" },
  { name: "ModelScope", trend: "评测工具可落地", verdict: "开源评测框架可以支撑可重复的业务场景比较。", action: "将场景题接入 EvalScope 验证。" }
];
const evalRows = [
  ["模型 A（演示）", "91 / 100", "94%", "1.42s", "¥0.031", "优先验证"],
  ["模型 B（演示）", "89 / 100", "90%", "1.68s", "¥0.047", "作为基准"],
  ["模型 C（演示）", "84 / 100", "86%", "0.91s", "¥0.012", "成本优先"],
];
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const priorityLabel = { high: "高优先级", medium: "中优先级", low: "低优先级" };

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
function renderEval() { $("#eval-body").innerHTML = evalRows.map((row) => `<tr>${row.map((cell, index) => `<td class="${index === 5 ? "recommendation" : ""}">${cell}</td>`).join("")}</tr>`).join(""); }
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
    const [signals, sources] = await Promise.all([fetch("data/signals.json"), fetch("data/sources.json")]);
    if (!signals.ok || !sources.ok) throw new Error("数据文件无法读取");
    state.signals = await signals.json(); state.sources = await sources.json();
    if (!Array.isArray(state.signals) || !Array.isArray(state.sources)) throw new Error("数据格式错误");
    renderAll(); setView(location.hash.slice(1) || "radar");
  } catch (error) {
    $("#pipeline-status").textContent = "本地数据加载失败";
    $("#signal-list").innerHTML = `<div class="empty">无法加载本地数据：${escapeHtml(error.message)}。请通过本地 HTTP 服务访问。</div>`;
    toast("数据加载失败，请检查本地服务");
  }
}
boot();
