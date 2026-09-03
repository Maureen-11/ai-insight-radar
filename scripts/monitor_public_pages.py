"""Detect meaningful text changes on configured public pages without publishing conclusions."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORK = ROOT / "work"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_html(payload: bytes, limit: int = 20000) -> str:
    value = payload.decode("utf-8", errors="replace")
    value = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", "\n", value)
    lines = [" ".join(html.unescape(line).split()) for line in value.splitlines()]
    return "\n".join(line for line in lines if len(line) > 2)[:limit]


def fetch(url: str, timeout: int = 20) -> bytes:
    request = Request(url, headers={"User-Agent": "AI-Insight-Radar/0.7 (+public research monitor)", "Accept": "text/html"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def diff_summary(before: str, after: str) -> str:
    additions = [line[2:] for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line.startswith("+ ")]
    return "；".join(additions[:3])[:360] or "页面文本发生变化，需人工打开来源复核。"


def monitor(sources, snapshots, fetcher=fetch, timeout=20):
    changes, health = [], []
    checked_at = now()
    for source in sources:
        if not source.get("enabled", True) or source.get("kind") != "page":
            continue
        try:
            text = clean_html(fetcher(source["url"], timeout))
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            previous = snapshots.get(source["id"])
            if previous and previous.get("hash") != digest:
                change_id = "change-" + hashlib.sha256(f"{source['id']}|{digest}".encode()).hexdigest()[:16]
                changes.append({"id": change_id, "sourceId": source["id"], "sourceName": source["name"], "url": source["url"],
                                "previousHash": previous.get("hash"), "currentHash": digest, "summary": diff_summary(previous.get("text", ""), text),
                                "detectedAt": checked_at, "status": "待复核"})
            snapshots[source["id"]] = {"hash": digest, "text": text, "checkedAt": checked_at, "url": source["url"]}
            health.append({"sourceId": source["id"], "name": source["name"], "status": "ok", "checkedAt": checked_at, "lastHash": digest[:12]})
        except Exception as error:
            health.append({"sourceId": source.get("id", "unknown"), "name": source.get("name", "unknown"), "status": "failed", "checkedAt": checked_at, "error": str(error)[:200]})
    return snapshots, changes, health


def read(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=DATA / "sources.json")
    parser.add_argument("--state", type=Path, default=WORK / "page-snapshots.json")
    parser.add_argument("--changes", type=Path, default=WORK / "page-changes.json")
    parser.add_argument("--health", type=Path, default=DATA / "source-health.json")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    snapshots, changes, health = monitor(read(args.sources, []), read(args.state, {}), timeout=args.timeout)
    existing = read(args.changes, [])
    known = {item.get("id") for item in existing}
    merged = existing + [item for item in changes if item["id"] not in known]
    for path in (args.state, args.changes, args.health): path.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.changes.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.health.write_text(json.dumps({"generatedAt": now(), "sources": health}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checked": len(health), "changes": len(changes), "failed": sum(x["status"] == "failed" for x in health)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

