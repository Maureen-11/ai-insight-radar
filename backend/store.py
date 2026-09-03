from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
DATA = ROOT / "data"
DEFAULT_DB = WORK / "research.db"

VALID_STATUSES = {"pending", "needs_verification", "approved", "ignored", "returned"}
VALID_PRIORITIES = {"high", "medium", "low"}
WATCH_TERMS = ("model", "模型", "api", "agent", "benchmark", "eval", "release", "pricing", "价格", "安全", "context")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def json_text(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def parse_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (value or "").lower())


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def research_score(item: dict[str, Any], duplicate_count: int = 0, now: datetime | None = None) -> tuple[float, list[str]]:
    now = now or datetime.now(timezone.utc)
    source_type = str(item.get("sourceType") or item.get("source", {}).get("type") or "")
    source_points = 28 if any(key in source_type.lower() for key in ("official", "官方", "github releases")) else 18
    reasons = [f"来源 {source_points}"]
    published = parse_date(item.get("publishedAt") or item.get("source", {}).get("publishedAt"))
    if published:
        age = max(0, (now - published.astimezone(timezone.utc)).days)
        freshness = max(0, 32 - min(age, 32))
    else:
        freshness = 4
    reasons.append(f"时效 {freshness}")
    haystack = " ".join([str(item.get("title", "")), str(item.get("summary", "")), " ".join(item.get("entities", []))]).lower()
    hits = [term for term in WATCH_TERMS if term in haystack]
    relevance = min(30, len(set(hits)) * 6)
    reasons.append(f"关注词 {relevance}")
    completeness = 10 if item.get("url") and item.get("title") and published else 4
    penalty = min(30, duplicate_count * 10)
    if penalty:
        reasons.append(f"疑似重复 -{penalty}")
    return round(max(0, min(100, source_points + freshness + relevance + completeness - penalty)), 1), reasons


class ResearchStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def session(self):
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.session() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_items (
                  id TEXT PRIMARY KEY, source_id TEXT, source_name TEXT, source_type TEXT,
                  category TEXT, entities_json TEXT NOT NULL DEFAULT '[]', title TEXT NOT NULL,
                  url TEXT NOT NULL UNIQUE, published_at TEXT, summary TEXT, status TEXT NOT NULL DEFAULT 'pending',
                  conclusion TEXT, why_now TEXT, impact_json TEXT NOT NULL DEFAULT '[]', action_json TEXT NOT NULL DEFAULT '[]',
                  questions_json TEXT NOT NULL DEFAULT '[]',
                  priority TEXT NOT NULL DEFAULT 'medium', confidence REAL NOT NULL DEFAULT 0.5,
                  reviewed INTEGER NOT NULL DEFAULT 0, research_score REAL NOT NULL DEFAULT 0,
                  score_reasons_json TEXT NOT NULL DEFAULT '[]', normalized_title TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_review_status_score ON review_items(status, research_score DESC);
                CREATE INDEX IF NOT EXISTS idx_review_published ON review_items(published_at DESC);
                CREATE TABLE IF NOT EXISTS page_changes (
                  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, url TEXT NOT NULL, previous_hash TEXT,
                  current_hash TEXT NOT NULL, change_summary TEXT, detected_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
                );
                CREATE TABLE IF NOT EXISTS eval_reviews (
                  configuration TEXT NOT NULL, case_id TEXT NOT NULL, response_excerpt TEXT,
                  factuality INTEGER, completeness INTEGER, citation_correctness INTEGER, structured_usability INTEGER,
                  issue_type TEXT NOT NULL DEFAULT '待标注', reviewer_note TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
                  updated_at TEXT NOT NULL, PRIMARY KEY(configuration, case_id)
                );
                CREATE TABLE IF NOT EXISTS experiment_runs (
                  run_id TEXT PRIMARY KEY, dataset_version TEXT, prompt_version TEXT, config_hash TEXT,
                  run_at TEXT, result_json TEXT NOT NULL
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(review_items)")}
            if "questions_json" not in columns:
                db.execute("ALTER TABLE review_items ADD COLUMN questions_json TEXT NOT NULL DEFAULT '[]'")

    def import_items(self, items: list[dict[str, Any]], approved: bool = False) -> int:
        counts: dict[str, int] = {}
        for item in items:
            key = normalized_title(item.get("title", ""))
            counts[key] = counts.get(key, 0) + 1
        inserted = 0
        with self.session() as db:
            for item in items:
                source = item.get("source") or {}
                source_id = item.get("sourceId") or source.get("name") or "unknown"
                source_name = item.get("sourceName") or source.get("name") or "来源待补充"
                source_type = item.get("sourceType") or source.get("type") or "公开来源"
                url = item.get("url") or source.get("url")
                if not item.get("title") or not url:
                    continue
                title_key = normalized_title(item["title"])
                score, reasons = research_score(item, max(0, counts.get(title_key, 1) - 1))
                item_id = item.get("id") or "item-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                status = "approved" if approved or item.get("reviewed") else "pending"
                reviewed = 1 if status == "approved" else 0
                timestamp = utc_now()
                before = db.total_changes
                db.execute(
                    """INSERT OR IGNORE INTO review_items
                    (id,source_id,source_name,source_type,category,entities_json,title,url,published_at,summary,status,
                     conclusion,why_now,impact_json,action_json,questions_json,priority,confidence,reviewed,research_score,score_reasons_json,
                     normalized_title,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (item_id, source_id, source_name, source_type, item.get("category", "生态"), json_text(item.get("entities")),
                     item["title"], url, item.get("publishedAt") or source.get("publishedAt"), item.get("summary") or (item.get("evidence") or [{}])[0].get("note", ""), status,
                     item.get("conclusion") or item.get("draftConclusion", ""), item.get("whyNow", ""),
                     json_text(item.get("impact") or item.get("draftImpact")), json_text(item.get("action") or item.get("draftAction")),
                     json_text(item.get("questions")),
                     item.get("priority", "medium"), float(item.get("confidence", 0.5)), reviewed, score, json_text(reasons),
                     title_key, item.get("collectedAt", timestamp), timestamp),
                )
                inserted += db.total_changes - before
        return inserted

    def bootstrap(self, inbox_path: Path | None = None, signals_path: Path | None = None) -> dict[str, int]:
        inbox_path = inbox_path or (WORK / "inbox.json")
        legacy = DATA / "inbox.json"
        if not inbox_path.exists() and legacy.exists():
            inbox_path = legacy
        signals_path = signals_path or (DATA / "signals.json")
        inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else []
        signals = json.loads(signals_path.read_text(encoding="utf-8")) if signals_path.exists() else []
        return {"inboxImported": self.import_items(inbox), "signalsImported": self.import_items(signals, approved=True)}

    def import_eval_data(self, review_path: Path | None = None, responses_path: Path | None = None, results_path: Path | None = None) -> int:
        review_paths = [review_path] if review_path else [DATA / "eval-review-template.json", DATA / "model-review.json"]
        responses_path = responses_path or (WORK / "eval-runs" / "latest-responses.json")
        results_path = results_path or (DATA / "eval-results.json")
        samples_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for index, candidate in enumerate(review_paths):
            if not candidate or not candidate.exists():
                continue
            review = json.loads(candidate.read_text(encoding="utf-8"))
            for sample in review.get("samples", []):
                key = (sample["configuration"], sample["caseId"])
                if index == 0 or key in samples_by_key:
                    samples_by_key[key] = {**samples_by_key.get(key, {}), **sample}
        responses = json.loads(responses_path.read_text(encoding="utf-8")) if responses_path.exists() else []
        response_map = {(row.get("configuration"), row.get("caseId")): row.get("response", "")[:1200] for row in responses}
        with self.session() as db:
            for sample in samples_by_key.values():
                key = (sample["configuration"], sample["caseId"])
                db.execute(
                    """INSERT OR IGNORE INTO eval_reviews
                    (configuration,case_id,response_excerpt,factuality,completeness,citation_correctness,structured_usability,
                     issue_type,reviewer_note,status,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (*key, response_map.get(key, ""), sample.get("factuality_1_to_5"), sample.get("completeness_1_to_5"),
                     sample.get("citation_correctness_1_to_5"), sample.get("structured_usability_1_to_5"),
                     sample.get("issueType", "待标注"), sample.get("reviewerNote", ""), "pending", utc_now()),
                )
            if results_path.exists():
                result = json.loads(results_path.read_text(encoding="utf-8"))
                run_at = result.get("runAt", "unknown")
                config_hash = hashlib.sha256(json.dumps(result.get("configurations", []), sort_keys=True).encode()).hexdigest()[:16]
                run_id = f"{result.get('datasetVersion','dataset')}@{run_at}"
                db.execute("INSERT OR REPLACE INTO experiment_runs VALUES (?,?,?,?,?,?)",
                           (run_id, result.get("datasetVersion"), "prompt-v1", config_hash, run_at, json_text(result)))
        return len(samples_by_key)

    def list_items(self, status: str = "pending", limit: int = 50, offset: int = 0, query: str = "") -> list[dict[str, Any]]:
        where, values = [], []
        if status != "all":
            where.append("status = ?"); values.append(status)
        if query:
            where.append("(title LIKE ? OR summary LIKE ? OR source_name LIKE ?)")
            term = f"%{query}%"; values.extend([term, term, term])
        clause = " WHERE " + " AND ".join(where) if where else ""
        sql = f"SELECT * FROM review_items{clause} ORDER BY research_score DESC, published_at DESC LIMIT ? OFFSET ?"
        values.extend([min(max(limit, 1), 200), max(offset, 0)])
        with self.session() as db:
            return [self._item(row) for row in db.execute(sql, values)]

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        with self.session() as db:
            row = db.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
            return self._item(row) if row else None

    def update_item(self, item_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {"status", "source_name", "source_type", "category", "title", "url", "published_at", "summary", "conclusion", "why_now", "priority", "confidence"}
        json_fields = {"entities": "entities_json", "impact": "impact_json", "action": "action_json", "questions": "questions_json"}
        assignments, values = [], []
        for key, value in changes.items():
            if key in allowed:
                if key == "status" and value not in VALID_STATUSES:
                    raise ValueError("invalid status")
                if key == "priority" and value not in VALID_PRIORITIES:
                    raise ValueError("invalid priority")
                assignments.append(f"{key} = ?"); values.append(value)
            elif key in json_fields:
                assignments.append(f"{json_fields[key]} = ?"); values.append(json_text(value))
        if not assignments:
            raise ValueError("no editable fields")
        assignments.append("updated_at = ?"); values.append(utc_now()); values.append(item_id)
        with self.session() as db:
            cursor = db.execute(f"UPDATE review_items SET {', '.join(assignments)} WHERE id = ?", values)
            if not cursor.rowcount:
                raise KeyError(item_id)
        return self.get_item(item_id) or {}

    def publish_item(self, item_id: str) -> dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            raise KeyError(item_id)
        missing = [key for key in ("conclusion", "whyNow", "impact", "action", "publishedAt", "url") if not item.get(key)]
        if missing:
            raise ValueError("发布前缺少字段: " + ", ".join(missing))
        with self.session() as db:
            db.execute("UPDATE review_items SET status='approved', reviewed=1, updated_at=? WHERE id=?", (utc_now(), item_id))
        return self.get_item(item_id) or {}

    def summary(self) -> dict[str, int]:
        with self.session() as db:
            rows = db.execute("SELECT status, COUNT(*) count FROM review_items GROUP BY status").fetchall()
            result = {row["status"]: row["count"] for row in rows}
            result["total"] = sum(result.values())
            result["evalPending"] = db.execute("SELECT COUNT(*) FROM eval_reviews WHERE status != 'complete'").fetchone()[0]
            return result

    def import_page_changes(self, path: Path | None = None) -> int:
        path = path or (WORK / "page-changes.json")
        if not path.exists():
            return 0
        changes = json.loads(path.read_text(encoding="utf-8"))
        inserted = 0
        with self.session() as db:
            for item in changes:
                before = db.total_changes
                db.execute("INSERT OR IGNORE INTO page_changes VALUES (?,?,?,?,?,?,?,?)",
                           (item["id"], item["sourceId"], item["url"], item.get("previousHash"), item["currentHash"],
                            item.get("summary", ""), item["detectedAt"], "pending"))
                inserted += db.total_changes - before
        return inserted

    def list_page_changes(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as db:
            return [dict(row) for row in db.execute("SELECT * FROM page_changes ORDER BY detected_at DESC LIMIT ?", (min(max(limit, 1), 200),))]

    def list_eval_reviews(self) -> list[dict[str, Any]]:
        with self.session() as db:
            return [dict(row) for row in db.execute("SELECT * FROM eval_reviews ORDER BY configuration, case_id")]

    def update_eval_review(self, configuration: str, case_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        field_map = {"factuality": "factuality", "completeness": "completeness", "citationCorrectness": "citation_correctness",
                     "structuredUsability": "structured_usability", "issueType": "issue_type", "reviewerNote": "reviewer_note"}
        assignments, values = [], []
        for key, column in field_map.items():
            if key not in changes:
                continue
            value = changes[key]
            if key in {"factuality", "completeness", "citationCorrectness", "structuredUsability"} and value is not None and not 1 <= int(value) <= 5:
                raise ValueError("scores must be between 1 and 5")
            assignments.append(f"{column}=?"); values.append(value)
        if not assignments:
            raise ValueError("no editable fields")
        completed = all(changes.get(key) is not None for key in ("factuality", "completeness", "citationCorrectness", "structuredUsability"))
        assignments.extend(["status=?", "updated_at=?"]); values.extend(["complete" if completed else "pending", utc_now(), configuration, case_id])
        with self.session() as db:
            db.execute(f"UPDATE eval_reviews SET {', '.join(assignments)} WHERE configuration=? AND case_id=?", values)
            row = db.execute("SELECT * FROM eval_reviews WHERE configuration=? AND case_id=?", (configuration, case_id)).fetchone()
            if not row:
                raise KeyError(f"{configuration}/{case_id}")
            return dict(row)

    def export_public(self, data_dir: Path | str = DATA) -> dict[str, Any]:
        data_dir = Path(data_dir); data_dir.mkdir(parents=True, exist_ok=True)
        with self.session() as db:
            approved = [self._item(row) for row in db.execute("SELECT * FROM review_items WHERE status='approved' ORDER BY published_at DESC")]
        signals = [self._signal(item) for item in approved]
        generated_at = utc_now()
        actions = []
        for signal in signals[:8]:
            for action in signal["action"]:
                if action not in actions:
                    actions.append(action)
        report = {"schemaVersion": "0.7.0", "generatedAt": generated_at, "title": "AI 行业策略周报",
                  "judgements": [{"signalId": item["id"], "conclusion": item["conclusion"], "whyNow": item["whyNow"],
                                  "impact": item["impact"], "source": item["source"]} for item in signals[:5]],
                  "nextActions": actions[:8], "reviewedOnly": True}
        timeline = [{"id": item["id"], "occurredAt": item["source"]["publishedAt"], "category": item["category"],
                     "entities": item["entities"], "title": item["title"], "conclusion": item["conclusion"], "source": item["source"]} for item in signals]
        (data_dir / "signals.json").write_text(json.dumps(signals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (data_dir / "weekly-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (data_dir / "vendor-timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"signals": len(signals), "reportJudgements": len(report["judgements"]), "timelineEvents": len(timeline), "generatedAt": generated_at}

    @staticmethod
    def _item(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "sourceId": row["source_id"], "sourceName": row["source_name"], "sourceType": row["source_type"],
                "category": row["category"], "entities": parse_json(row["entities_json"], []), "title": row["title"], "url": row["url"],
                "publishedAt": row["published_at"], "summary": row["summary"], "status": row["status"], "conclusion": row["conclusion"],
                "whyNow": row["why_now"], "impact": parse_json(row["impact_json"], []), "action": parse_json(row["action_json"], []),
                "questions": parse_json(row["questions_json"], []),
                "priority": row["priority"], "confidence": row["confidence"], "reviewed": bool(row["reviewed"]),
                "researchScore": row["research_score"], "scoreReasons": parse_json(row["score_reasons_json"], []), "updatedAt": row["updated_at"]}

    @staticmethod
    def _signal(item: dict[str, Any]) -> dict[str, Any]:
        return {"id": item["id"], "category": item["category"], "title": item["title"], "conclusion": item["conclusion"],
                "whyNow": item["whyNow"], "impact": item["impact"], "action": item["action"], "entities": item["entities"],
                "source": {"name": item["sourceName"], "url": item["url"], "publishedAt": item["publishedAt"], "type": item["sourceType"]},
                "evidence": [{"label": item["sourceName"], "url": item["url"], "note": (item.get("summary") or "")[:280]}],
                "questions": item.get("questions", []),
                "confidence": item["confidence"], "priority": item["priority"], "status": "已复核", "reviewed": True}
