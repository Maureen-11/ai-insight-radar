"""Collect public RSS/Atom metadata into a local review inbox.

This program intentionally stores only title, published date, canonical URL and a
short plain-text summary. It does not call an LLM, use credentials, or promote
an item into data/signals.json. A human must review each inbox item first.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NS = {"atom": "http://www.w3.org/2005/Atom", "content": "http://purl.org/rss/1.0/modules/content/"}


def text(node: ET.Element | None) -> str:
    return "" if node is None else " ".join("".join(node.itertext()).split())


def first_node(*nodes: ET.Element | None) -> ET.Element | None:
    return next((node for node in nodes if node is not None), None)


def clean_summary(value: str, limit: int = 280) -> str:
    value = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    value = " ".join(value.split())
    return value[:limit].rstrip()


def stable_id(source_id: str, url: str, title: str, published_at: str) -> str:
    digest = hashlib.sha256(f"{source_id}|{url}|{title}|{published_at}".encode("utf-8")).hexdigest()[:16]
    return f"inbox-{digest}"


def draft_fields(category: str) -> dict[str, Any]:
    templates = {
        "模型": ("模型与版本更新需要用业务题验证，不能直接等同于采购结论。", ["确认更新涉及的能力边界", "加入同口径场景评测"], ["记录质量、延迟和单题成本", "保留异常样本供人工复核"]),
        "产品": ("产品动态需要映射到现有工作流，才能判断是否有实际影响。", ["检查对用户流程和证据链的影响", "识别权限与可审计要求"], ["选择一个工作流做小范围验证", "补充验收指标"]),
        "生态": ("开源生态动态需要同时评估部署、治理与维护成本。", ["检查部署与运维依赖", "评估评测和可观测能力"], ["阅读版本说明", "在本地 fixture 上验证"]),
    }
    conclusion, impact, action = templates.get(category, templates["生态"])
    return {"draftConclusion": conclusion, "draftImpact": impact, "draftAction": action}


def parse_feed(payload: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    entries = root.findall("atom:entry", NS)
    atom = bool(entries)
    if not atom:
        entries = root.findall("./channel/item") or root.findall(".//item")
    items = []
    for entry in entries:
        title = text(entry.find("atom:title", NS) if atom else entry.find("title"))
        if not title:
            continue
        if atom:
            link_node = next((link for link in entry.findall("atom:link", NS) if link.get("rel", "alternate") == "alternate" and link.get("href")), None)
            url = (link_node.get("href") if link_node is not None else "") or ""
            published = text(first_node(entry.find("atom:published", NS), entry.find("atom:updated", NS)))
            summary = text(first_node(entry.find("atom:summary", NS), entry.find("atom:content", NS)))
        else:
            url = text(entry.find("link"))
            published = text(entry.find("pubDate")) or text(entry.find("date"))
            summary = text(first_node(entry.find("description"), entry.find("content:encoded", NS)))
        if not url:
            continue
        created = {"id": stable_id(source["id"], url, title, published), "sourceId": source["id"], "sourceName": source["name"], "sourceType": source["type"], "category": source.get("category", "生态"), "entities": source.get("entities", []), "title": title, "url": url, "publishedAt": published or None, "summary": clean_summary(summary), "status": "待复核", "reviewed": False, "collectedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), **draft_fields(source.get("category", "生态"))}
        items.append(created)
    return items


def fetch(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"User-Agent": "AI-Insight-Radar/0.2 (+local research demo)", "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def collect(sources: list[dict[str, Any]], existing: list[dict[str, Any]], timeout: int, fetcher=fetch) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    known = {item.get("url") for item in existing} | {item.get("id") for item in existing}
    additions: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for source in sources:
        if not source.get("enabled", True):
            continue
        try:
            for item in parse_feed(fetcher(source["url"], timeout), source):
                if item["url"] not in known and item["id"] not in known:
                    additions.append(item)
                    known.add(item["url"]); known.add(item["id"])
        except (URLError, HTTPError, ET.ParseError, TimeoutError, OSError, ValueError) as error:
            failures.append({"source": source.get("name", source.get("id", "unknown")), "error": str(error)[:240]})
    return existing + additions, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public Atom/RSS metadata for manual review.")
    parser.add_argument("--sources", type=Path, default=DATA / "sources.json")
    parser.add_argument("--out", type=Path, default=DATA / "inbox.json")
    parser.add_argument("--report", type=Path, default=DATA / "collection-report.json")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    sources = read_json(args.sources, []); existing = read_json(args.out, [])
    if not isinstance(sources, list) or not isinstance(existing, list):
        raise SystemExit("sources.json 和 inbox.json 必须是 JSON 数组")
    merged, failures = collect(sources, existing, args.timeout)
    args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"collectedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "configuredSources": len(sources), "inboxBefore": len(existing), "added": len(merged) - len(existing), "inboxAfter": len(merged), "failures": failures, "note": "失败来源不会清空已有 inbox；所有条目均需人工复核后才能进入 signals.json。"}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
