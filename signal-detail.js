const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const priorityLabel = { high: "高优先级", medium: "中优先级", low: "低优先级" };
function list(items) { return items?.length ? `<ul>${items.map((item) => `<li>${escapeHtml(typeof item === "string" ? item : item.text || "")}</li>`).join("")}</ul>` : "<p>暂无待补充内容。</p>"; }
function refs(ids) { return (ids || []).map((id) => `<a class="evidence-ref" href="#evidence-${encodeURIComponent(id)}">[${escapeHtml(id)}]</a>`).join(" "); }
function dated(value) { if (!value) return "日期待补充"; const date = new Date(value); return Number.isNaN(date.valueOf()) ? escapeHtml(value) : date.toLocaleDateString("zh-CN"); }
function confidence(signal) {
  const value = signal.confidence;
  if (typeof value === "number") return { overall: value, sourceQuality: value, evidenceAgreement: value, scopeFitness: value, rationale: "旧版总分，尚未拆分依据。" };
  return value || { overall: 0, sourceQuality: 0, evidenceAgreement: 0, scopeFitness: 0, rationale: "尚未评估。" };
}
function evidenceLinkedRows(items, numbered = false) {
  if (!items?.length) return "<p>暂无待补充内容。</p>";
  return `<div class="reasoning-list">${items.map((item, index) => `<article><span class="reasoning-index">${numbered ? index + 1 : escapeHtml(item.id || index + 1)}</span><p>${escapeHtml(item.text || item)} <span class="inline-refs">${refs(item.evidenceIds)}</span></p></article>`).join("")}</div>`;
}
function impactCards(items) {
  return items?.length ? `<div class="decision-grid">${items.map((item) => `<article><span>${escapeHtml(item.area)}</span><p>${escapeHtml(item.impact)}</p></article>`).join("")}</div>` : "<p>暂无待补充内容。</p>";
}
function actionTable(items) {
  return items?.length ? `<div class="action-table">${items.map((item) => `<article><strong>${escapeHtml(item.action)}</strong><dl><div><dt>责任角色</dt><dd>${escapeHtml(item.ownerRole || item.owner)}</dd></div><div><dt>验证指标</dt><dd>${escapeHtml(item.metric)}</dd></div><div><dt>预期结果</dt><dd>${escapeHtml(item.expectedOutcome || item.expected)}</dd></div></dl></article>`).join("")}</div>` : "<p>暂无待补充内容。</p>";
}
async function boot() {
  const detail = $("#detail"); const id = new URLSearchParams(location.search).get("id");
  try {
    const response = await fetch("data/signals.json"); if (!response.ok) throw new Error("数据文件无法读取");
    const signals = await response.json(); const index = signals.findIndex((item) => item.id === id); const signal = signals[index];
    if (!signal) throw new Error("未找到该研究报告，链接可能已失效");
    const score = confidence(signal); const review = signal.review || {};
    document.title = `${signal.title} · AI Insight Radar`;
    detail.innerHTML = `<div class="detail-top"><span class="tag ${escapeHtml(signal.priority)}">${priorityLabel[signal.priority] || "待定"}</span><span class="tag neutral">${escapeHtml(signal.track || signal.category)}</span><span>${escapeHtml(signal.category)} · ${escapeHtml(signal.source.type)} · ${dated(signal.source.publishedAt)}</span></div>
      <div class="review-banner ${signal.reviewed ? "review-complete" : "review-pending"}"><strong>${signal.reviewed ? "人工复核已完成" : "研究草稿 · 待人工确认"}</strong><span>AI 草稿：${review.aiDrafted ? "已生成" : "未生成"} · 人工确认：${review.humanReviewed ? "已完成" : "未完成"} · 版本：${escapeHtml(review.version || "旧版")}</span></div>
      <h1>${escapeHtml(signal.title)}</h1>
      <section class="executive-block"><p class="section-kicker">核心判断</p><p class="detail-conclusion">${escapeHtml(signal.conclusion)}</p></section>
      <section><h2>研究问题</h2><p class="research-question">${escapeHtml(signal.researchQuestion || signal.whyNow)}</p></section>
      <section><h2>为什么现在重要</h2><p>${escapeHtml(signal.whyNow)}</p></section>
      <section><div class="section-heading"><h2>${signal.reviewed ? "已确认事实" : "来源支持的事实陈述"}</h2><span>${signal.reviewed ? "事实与来源逐条关联" : "已完成证据映射，仍待项目负责人核验"}</span></div>${evidenceLinkedRows(signal.observations)}</section>
      <section><div class="section-heading"><h2>分析与推理</h2><span>以下为本项目判断，不是来源原文</span></div>${evidenceLinkedRows(signal.analysis, true)}</section>
      <section class="boundary-section"><h2>反例与适用边界</h2><div class="detail-grid"><div><h3>可能削弱结论的情况</h3>${evidenceLinkedRows(signal.counterEvidence, true)}</div><div><h3>当前研究限制</h3>${list(signal.limitations)}</div></div></section>
      <section><h2>对业务决策的影响</h2>${impactCards(signal.decisionImpact)}</section>
      <section><h2>建议行动与验证方法</h2>${actionTable(signal.recommendedActions)}</section>
      <section><h2>待验证问题</h2>${list(signal.questions)}</section>
      <section><h2>置信度为什么是 ${Math.round((score.overall || 0) * 100)}%</h2><div class="confidence-grid"><article><strong>${Math.round((score.sourceQuality || 0) * 100)}%</strong><span>来源质量</span></article><article><strong>${Math.round((score.evidenceAgreement || 0) * 100)}%</strong><span>证据一致性</span></article><article><strong>${Math.round((score.scopeFitness || 0) * 100)}%</strong><span>适用范围</span></article></div><p class="confidence-note">${escapeHtml(score.rationale)}</p></section>
      <section><h2>相关实体</h2><p>${(signal.entities || []).map((entity) => `<span class="tag neutral">${escapeHtml(entity)}</span>`).join(" ")}</p></section>
      <section><div class="section-heading"><h2>完整证据目录</h2><span>${signal.evidence?.length || 0} 个可追溯来源</span></div><div class="evidence-list">${(signal.evidence || []).map((evidence) => `<article id="evidence-${escapeHtml(evidence.id || "unknown")}"><div class="evidence-meta"><span class="evidence-code">${escapeHtml(evidence.id || "E?")}</span><span>${escapeHtml(evidence.sourceType || "公开来源")}</span><span>${escapeHtml(evidence.evidenceRole || "背景")}</span><span>${evidence.verified ? "已核验" : "待核验"}</span></div><a href="${escapeHtml(evidence.url)}" target="_blank" rel="noreferrer">${escapeHtml(evidence.title || evidence.label)} ↗</a><p>${escapeHtml(evidence.sourceName || "")} · 发布：${dated(evidence.publishedAt)} · 访问：${dated(evidence.accessedAt)}</p><p>${escapeHtml(evidence.note || "")}</p></article>`).join("")}</div><p class="source-note">本页仅保存事实摘要、链接与研究判断，不转载第三方文章全文。厂商资料属于官方主张，本项目实测仅适用于所列题集和运行边界。</p></section>`;
    const previous = signals[(index - 1 + signals.length) % signals.length]; const next = signals[(index + 1) % signals.length];
    $("#previous").href = `signal.html?id=${encodeURIComponent(previous.id)}`; $("#next").href = `signal.html?id=${encodeURIComponent(next.id)}`;
  } catch (error) { detail.innerHTML = `<h1>无法打开研究报告</h1><p>${escapeHtml(error.message)}</p><a class="text-link" href="index.html#radar">返回情报列表 →</a>`; $("#previous").hidden = true; $("#next").hidden = true; }
}
boot();
