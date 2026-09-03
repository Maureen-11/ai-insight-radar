"""Generate reviewed-only weekly report, timeline, Markdown archive, manifest and RSS."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def confidence_value(item):
    value = item.get("confidence", 0)
    return float(value.get("overall", 0) if isinstance(value, dict) else value or 0)


def generate(signals, output: Path, reports: Path, generated_at: datetime, feed_path: Path | None = None):
    reviewed = [
        item for item in signals
        if item.get("reviewed") and (item.get("review") or {}).get("humanReviewed") is True
    ]
    priority = {"high": 3, "medium": 2, "low": 1}
    reviewed.sort(key=lambda x: (priority.get(x.get("priority"), 0), confidence_value(x), x.get("source", {}).get("publishedAt", "")), reverse=True)
    actions = []
    for item in reviewed:
        for action in item.get("action", []):
            if action not in actions: actions.append(action)
    timestamp = generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    dual_path = output / "eval-dual-review-summary.json"
    dual = load(dual_path) if dual_path.exists() else None
    report = {"schemaVersion": "1.0.0", "generatedAt": timestamp, "title": "AI 行业策略周报", "reviewedOnly": True,
              "judgements": [{"signalId": item["id"], "researchQuestion": item.get("researchQuestion", ""),
                              "executiveSummary": item.get("executiveSummary", ""), "conclusion": item["conclusion"],
                              "whyNow": item.get("whyNow", ""), "impact": item.get("impact", []),
                              "evidenceCount": len(item.get("evidence", [])), "source": item["source"]} for item in reviewed[:5]], "nextActions": actions[:8]}
    if dual:
        report["modelEvaluation"] = {"status": dual.get("dualValidationStatus"), "sampleCount": dual.get("sampleCount"),
                                     "humanConfirmed": dual.get("humanConfirmed"), "findings": dual.get("findings", []),
                                     "nextActions": dual.get("nextActions", []), "privacy": dual.get("privacy")}
    timeline = [{"id": item["id"], "occurredAt": item["source"].get("publishedAt"), "category": item.get("category"),
                 "entities": item.get("entities", []), "title": item["title"], "conclusion": item["conclusion"], "source": item["source"]} for item in reviewed]
    output.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    (output / "weekly-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "vendor-timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    day = generated_at.date().isoformat(); report_path = reports / f"{day}.md"
    lines = [f"# AI 行业策略周报 · {day}", "", "> 仅汇总已由项目负责人确认发布的深度研究报告；自动简报不进入本区域。", ""]
    if not report["judgements"]:
        lines += ["本期暂无通过发布门槛的深度报告。", ""]
    for index, item in enumerate(report["judgements"], 1):
        lines += [f"## {index}. {item.get('executiveSummary') or item['conclusion']}", "", f"研究问题：{item.get('researchQuestion','')}", "",
                  f"核心判断：{item['conclusion']}", "", f"为什么现在：{item['whyNow']}", "",
                  "影响：" + "；".join(item["impact"]), "", f"证据条目：{item.get('evidenceCount', 0)} 个", "",
                  f"主来源：[{item['source']['name']}]({item['source']['url']}) · {item['source'].get('publishedAt','日期待补')}", ""]
    if dual:
        lines += ["## 模型评测双重验证", "", f"状态：{'AI 初评 + 人工确认完成' if dual.get('dualValidationStatus') == 'completed' else '人工确认进行中'}（{dual.get('humanConfirmed', 0)}/{dual.get('sampleCount', 0)}）", ""]
        lines += [f"- {value}" for value in dual.get("findings", [])] + [""]
        lines += ["后续动作："] + [f"- {value}" for value in dual.get("nextActions", [])] + [""]
    lines += ["## 下周行动", ""] + [f"- {value}" for value in report["nextActions"]]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    manifest = {"generatedAt": timestamp, "reports": [{"date": path.stem, "path": f"reports/{path.name}"} for path in sorted(reports.glob("*.md"), reverse=True)]}
    (output / "report-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rss_items = []
    for item in reviewed[:30]:
        source = item["source"]
        rss_items.append(f"<item><title>{escape(item['conclusion'])}</title><link>{escape(source['url'])}</link><guid>{escape(item['id'])}</guid><description>{escape('；'.join(item.get('impact', [])))}</description></item>")
    rss = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>AI Insight Radar</title><link>https://maureen-11.github.io/ai-insight-radar/</link><description>Reviewed AI industry signals</description><lastBuildDate>{format_datetime(generated_at)}</lastBuildDate>{"".join(rss_items)}</channel></rss>\n'
    feed_path = feed_path or (output.parent / "feed.xml")
    feed_path.write_text(rss, encoding="utf-8")
    return {"reviewed": len(reviewed), "report": str(report_path), "rssItems": len(rss_items)}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--signals", type=Path, default=DATA / "signals.json"); args = parser.parse_args()
    result = generate(load(args.signals), DATA, ROOT / "reports", datetime.now(timezone.utc)); print(json.dumps(result, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
