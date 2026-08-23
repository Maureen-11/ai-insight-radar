const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const priorityLabel = { high: "高优先级", medium: "中优先级", low: "低优先级" };
function list(items) { return items?.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "<p>暂无待补充内容。</p>"; }
async function boot() {
  const detail = $("#detail"); const id = new URLSearchParams(location.search).get("id");
  try {
    const response = await fetch("data/signals.json"); if (!response.ok) throw new Error("数据文件无法读取");
    const signals = await response.json(); const index = signals.findIndex((item) => item.id === id); const signal = signals[index];
    if (!signal) throw new Error("未找到该情报，链接可能已失效");
    document.title = `${signal.title} · AI Insight Radar`;
    detail.innerHTML = `<div class="detail-top"><span class="tag ${escapeHtml(signal.priority)}">${priorityLabel[signal.priority] || "待定"}</span><span>${escapeHtml(signal.category)} · ${escapeHtml(signal.source.type)} · ${escapeHtml(signal.source.publishedAt)}</span></div><p class="eyebrow">人工复核：${signal.reviewed ? "已完成" : "未完成"} · 置信度 ${Math.round((signal.confidence || 0) * 100)}% · 状态：${escapeHtml(signal.status || "待复核")}</p><h1>${escapeHtml(signal.title)}</h1><section><h2>结论</h2><p class="detail-conclusion">${escapeHtml(signal.conclusion)}</p></section><section><h2>为什么现在重要</h2><p>${escapeHtml(signal.whyNow)}</p></section><div class="detail-grid"><section><h2>影响对象</h2>${list(signal.impact)}</section><section><h2>建议行动</h2>${list(signal.action)}</section></div><section><h2>待验证问题</h2>${list(signal.questions)}</section><section><h2>相关实体</h2><p>${(signal.entities || []).map((entity) => `<span class="tag neutral">${escapeHtml(entity)}</span>`).join(" ")}</p></section><section><h2>证据与来源</h2><div class="evidence-list">${(signal.evidence || []).map((evidence) => `<article><a href="${escapeHtml(evidence.url)}" target="_blank" rel="noreferrer">${escapeHtml(evidence.label)} ↗</a><p>${escapeHtml(evidence.note || "")}</p></article>`).join("")}</div><p class="source-note">本页不转载第三方文章全文，只保存链接、日期与必要短说明。</p></section>`;
    const previous = signals[(index - 1 + signals.length) % signals.length]; const next = signals[(index + 1) % signals.length];
    $("#previous").href = `signal.html?id=${encodeURIComponent(previous.id)}`; $("#next").href = `signal.html?id=${encodeURIComponent(next.id)}`;
  } catch (error) { detail.innerHTML = `<h1>无法打开情报详情</h1><p>${escapeHtml(error.message)}</p><a class="text-link" href="index.html#radar">返回情报列表 →</a>`; $("#previous").hidden = true; $("#next").hidden = true; }
}
boot();
