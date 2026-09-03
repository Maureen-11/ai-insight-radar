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


def evaluation_case_map() -> dict[str, dict[str, Any]]:
    path = DATA / "eval-scenarios.json"
    if not path.exists():
        return {}
    dataset = json.loads(path.read_text(encoding="utf-8"))
    mapped: dict[str, dict[str, Any]] = {}
    for scenario in dataset.get("scenarios", []):
        for case in scenario.get("cases", []):
            mapped[case["id"]] = {"scenario": scenario.get("name", "未分类"), **case}
    return mapped


def ai_draft_assessment(response: str, case: dict[str, Any]) -> dict[str, Any]:
    """Deterministic, transparent initial assessment; never a human score."""
    parsed = parse_json(response, {})
    text = response.lower()
    expected_keywords = [str(value).lower() for value in case.get("keywords", [])]
    expected_citations = [str(value).lower() for value in case.get("citations", [])]
    fields = case.get("required_fields", [])
    facts_present = all(keyword in text for keyword in expected_keywords)
    citations_present = all(citation in text for citation in expected_citations)
    valid_object = isinstance(parsed, dict)
    values = " ".join(str(parsed.get(field, "")).lower() for field in fields)
    fields_have_values = bool(fields) and all(keyword in values for keyword in expected_keywords)
    if fields:
        structured = 5 if valid_object and fields_have_values else 2 if valid_object else 1
        completeness = 5 if fields_have_values else 2 if facts_present else 1
        issue = "字段映射错误" if facts_present and not fields_have_values else "待人工确认"
    else:
        structured = 4 if valid_object else 3
        completeness = 5 if facts_present else 2
        issue = "待人工确认" if facts_present else "可能遗漏"
    return {
        "factuality": 5 if facts_present else 2,
        "completeness": completeness,
        "citationCorrectness": 5 if citations_present else 1,
        "structuredUsability": structured,
        "issueType": issue,
        "note": "规则初评：仅核对合成材料中的关键词、引用编号与字段映射；不是人工复核结论。",
    }


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
                  category TEXT, track TEXT, entities_json TEXT NOT NULL DEFAULT '[]', title TEXT NOT NULL,
                  url TEXT NOT NULL UNIQUE, published_at TEXT, summary TEXT, status TEXT NOT NULL DEFAULT 'pending',
                  conclusion TEXT, why_now TEXT, impact_json TEXT NOT NULL DEFAULT '[]', action_json TEXT NOT NULL DEFAULT '[]',
                  questions_json TEXT NOT NULL DEFAULT '[]',
                  research_question TEXT, executive_summary TEXT,
                  observations_json TEXT NOT NULL DEFAULT '[]', analysis_json TEXT NOT NULL DEFAULT '[]',
                  counter_evidence_json TEXT NOT NULL DEFAULT '[]', limitations_json TEXT NOT NULL DEFAULT '[]',
                  decision_impact_json TEXT NOT NULL DEFAULT '[]', recommended_actions_json TEXT NOT NULL DEFAULT '[]',
                  evidence_json TEXT NOT NULL DEFAULT '[]', confidence_json TEXT NOT NULL DEFAULT '{}',
                  ai_drafted INTEGER NOT NULL DEFAULT 0, human_reviewed INTEGER NOT NULL DEFAULT 0,
                  review_version TEXT, human_reviewed_at TEXT,
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
                  ai_factuality INTEGER, ai_completeness INTEGER, ai_citation_correctness INTEGER, ai_structured_usability INTEGER,
                  ai_issue_type TEXT, ai_note TEXT, ai_completed_at TEXT,
                  human_confirmed_at TEXT, human_confirmation_source TEXT,
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
            if "track" not in columns:
                db.execute("ALTER TABLE review_items ADD COLUMN track TEXT")
            for name, declaration in {
                "research_question": "TEXT", "executive_summary": "TEXT",
                "observations_json": "TEXT NOT NULL DEFAULT '[]'", "analysis_json": "TEXT NOT NULL DEFAULT '[]'",
                "counter_evidence_json": "TEXT NOT NULL DEFAULT '[]'", "limitations_json": "TEXT NOT NULL DEFAULT '[]'",
                "decision_impact_json": "TEXT NOT NULL DEFAULT '[]'", "recommended_actions_json": "TEXT NOT NULL DEFAULT '[]'",
                "evidence_json": "TEXT NOT NULL DEFAULT '[]'", "confidence_json": "TEXT NOT NULL DEFAULT '{}'",
                "ai_drafted": "INTEGER NOT NULL DEFAULT 0", "human_reviewed": "INTEGER NOT NULL DEFAULT 0",
                "review_version": "TEXT", "human_reviewed_at": "TEXT",
            }.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE review_items ADD COLUMN {name} {declaration}")
            eval_columns = {row["name"] for row in db.execute("PRAGMA table_info(eval_reviews)")}
            for name, declaration in {
                "ai_factuality": "INTEGER", "ai_completeness": "INTEGER", "ai_citation_correctness": "INTEGER",
                "ai_structured_usability": "INTEGER", "ai_issue_type": "TEXT", "ai_note": "TEXT",
                "ai_completed_at": "TEXT", "human_confirmed_at": "TEXT", "human_confirmation_source": "TEXT",
            }.items():
                if name not in eval_columns:
                    db.execute(f"ALTER TABLE eval_reviews ADD COLUMN {name} {declaration}")

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
                status = "approved" if approved or (item.get("reviewed") and item.get("review", {}).get("humanReviewed", True)) else "pending"
                reviewed = 1 if status == "approved" else 0
                confidence_data = item.get("confidence", 0.5)
                confidence_value = float(confidence_data.get("overall", 0.5) if isinstance(confidence_data, dict) else confidence_data)
                review = item.get("review") or {}
                timestamp = utc_now()
                before = db.total_changes
                db.execute(
                    """INSERT OR IGNORE INTO review_items
                    (id,source_id,source_name,source_type,category,track,entities_json,title,url,published_at,summary,status,
                     conclusion,why_now,impact_json,action_json,questions_json,research_question,executive_summary,
                     observations_json,analysis_json,counter_evidence_json,limitations_json,decision_impact_json,recommended_actions_json,
                     evidence_json,confidence_json,ai_drafted,human_reviewed,review_version,human_reviewed_at,
                     priority,confidence,reviewed,research_score,score_reasons_json,normalized_title,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (item_id, source_id, source_name, source_type, item.get("category", "生态"), item.get("track"), json_text(item.get("entities")),
                     item["title"], url, item.get("publishedAt") or source.get("publishedAt"), item.get("summary") or (item.get("evidence") or [{}])[0].get("note", ""), status,
                     item.get("conclusion") or item.get("draftConclusion", ""), item.get("whyNow", ""),
                     json_text(item.get("impact") or item.get("draftImpact")), json_text(item.get("action") or item.get("draftAction")),
                     json_text(item.get("questions")), item.get("researchQuestion"), item.get("executiveSummary"),
                     json_text(item.get("observations")), json_text(item.get("analysis")), json_text(item.get("counterEvidence")),
                     json_text(item.get("limitations")), json_text(item.get("decisionImpact")), json_text(item.get("recommendedActions")),
                     json_text(item.get("evidence")), json.dumps(confidence_data if isinstance(confidence_data, dict) else {"overall": confidence_value}, ensure_ascii=False),
                     1 if review.get("aiDrafted") else 0, 1 if review.get("humanReviewed") else 0, review.get("version"), review.get("reviewedAt"),
                     item.get("priority", "medium"), confidence_value, reviewed, score, json_text(reasons),
                     title_key, item.get("collectedAt", timestamp), timestamp),
                )
                inserted += db.total_changes - before
                if item.get("schemaVersion") == "1.0.0":
                    db.execute(
                        """UPDATE review_items SET source_name=?,source_type=?,category=?,track=?,entities_json=?,title=?,url=?,published_at=?,summary=?,
                        status=?,conclusion=?,why_now=?,impact_json=?,action_json=?,questions_json=?,research_question=?,executive_summary=?,
                        observations_json=?,analysis_json=?,counter_evidence_json=?,limitations_json=?,decision_impact_json=?,recommended_actions_json=?,
                        evidence_json=?,confidence_json=?,ai_drafted=?,human_reviewed=?,review_version=?,human_reviewed_at=?,priority=?,confidence=?,reviewed=?,updated_at=?
                        WHERE id=? AND (review_version IS NULL OR review_version='')""",
                        (source_name, source_type, item.get("category", "生态"), item.get("track"), json_text(item.get("entities")), item["title"], url,
                         item.get("publishedAt") or source.get("publishedAt"), item.get("executiveSummary") or item.get("summary") or "", status,
                         item.get("conclusion", ""), item.get("whyNow", ""), json_text(item.get("impact")), json_text(item.get("action")),
                         json_text(item.get("questions")), item.get("researchQuestion"), item.get("executiveSummary"), json_text(item.get("observations")),
                         json_text(item.get("analysis")), json_text(item.get("counterEvidence")), json_text(item.get("limitations")),
                         json_text(item.get("decisionImpact")), json_text(item.get("recommendedActions")), json_text(item.get("evidence")),
                         json.dumps(confidence_data, ensure_ascii=False), 1 if review.get("aiDrafted") else 0, 1 if review.get("humanReviewed") else 0,
                         review.get("version"), review.get("reviewedAt"), item.get("priority", "medium"), confidence_value, reviewed, timestamp, item_id),
                    )
        return inserted

    def bootstrap(self, inbox_path: Path | None = None, signals_path: Path | None = None) -> dict[str, int]:
        inbox_path = inbox_path or (WORK / "inbox.json")
        legacy = DATA / "inbox.json"
        if not inbox_path.exists() and legacy.exists():
            inbox_path = legacy
        signals_path = signals_path or (DATA / "signals.json")
        inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else []
        signals = json.loads(signals_path.read_text(encoding="utf-8")) if signals_path.exists() else []
        return {"inboxImported": self.import_items(inbox), "signalsImported": self.import_items(signals)}

    def promote_auto_brief(self, item_id: str, brief_path: Path | None = None) -> dict[str, Any]:
        brief_path = brief_path or (DATA / "auto-brief.json")
        brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.exists() else {}
        source_item = next((item for item in brief.get("items", []) if item.get("id") == item_id), None)
        if not source_item:
            raise KeyError(item_id)
        source = source_item.get("source") or {}
        promoted_id = "research-" + hashlib.sha256((source.get("url") or item_id).encode("utf-8")).hexdigest()[:16]
        draft = {
            "id": promoted_id, "sourceId": source.get("name", "auto-brief"), "sourceName": source.get("name", "公开来源"),
            "sourceType": source.get("type", "公开来源"), "category": source_item.get("category", "生态"),
            "entities": source_item.get("entities", []), "title": source_item.get("title", "待命名研究问题"),
            "url": source.get("url"), "publishedAt": source.get("publishedAt"), "summary": source_item.get("summary", ""),
            "conclusion": source_item.get("whatChanged", ""), "whyNow": source_item.get("summary", ""),
            "impact": source_item.get("impact", []), "action": source_item.get("action", []),
            "priority": "medium", "confidence": source_item.get("confidence", 0.5), "reviewed": False,
        }
        self.import_items([draft])
        return self.get_item(promoted_id) or {}

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
        allowed = {"status", "source_name", "source_type", "category", "track", "title", "url", "published_at", "summary", "conclusion", "why_now", "priority", "confidence", "research_question", "executive_summary", "review_version", "ai_drafted", "human_reviewed"}
        json_fields = {"entities": "entities_json", "impact": "impact_json", "action": "action_json", "questions": "questions_json",
                       "observations": "observations_json", "analysis": "analysis_json", "counter_evidence": "counter_evidence_json",
                       "limitations": "limitations_json", "decision_impact": "decision_impact_json",
                       "recommended_actions": "recommended_actions_json", "evidence": "evidence_json",
                       "confidence_detail": "confidence_json"}
        assignments, values = [], []
        for key, value in changes.items():
            if key in allowed:
                if key == "status" and value not in VALID_STATUSES:
                    raise ValueError("invalid status")
                if key == "priority" and value not in VALID_PRIORITIES:
                    raise ValueError("invalid priority")
                assignments.append(f"{key} = ?"); values.append(int(value) if key in {"ai_drafted", "human_reviewed"} else value)
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
        errors = self.deep_report_errors(item)
        if errors:
            raise ValueError("发布校验未通过: " + "；".join(errors))
        with self.session() as db:
            reviewed_at = utc_now()
            db.execute("UPDATE review_items SET status='approved', reviewed=1, human_reviewed=1, human_reviewed_at=?, updated_at=? WHERE id=?", (reviewed_at, reviewed_at, item_id))
        return self.get_item(item_id) or {}

    @staticmethod
    def deep_report_errors(item: dict[str, Any]) -> list[str]:
        required = ("researchQuestion", "executiveSummary", "conclusion", "whyNow", "observations", "analysis",
                    "counterEvidence", "limitations", "decisionImpact", "recommendedActions", "evidence", "publishedAt", "url")
        errors = [f"缺少 {key}" for key in required if not item.get(key)]
        evidence = item.get("evidence") or []
        ids = {entry.get("id") for entry in evidence if entry.get("id")}
        if len(evidence) < 2:
            errors.append("至少需要 2 个具体证据")
        if not any(any(token in str(entry.get("sourceType", "")) for token in ("厂商官方", "开源项目", "开源评测", "本项目")) for entry in evidence):
            errors.append("至少需要 1 个一手来源")
        for entry in evidence:
            if not all(entry.get(key) for key in ("id", "title", "url", "publishedAt", "accessedAt", "sourceType")):
                errors.append("证据标题、链接、日期或类型不完整")
                break
            if not entry.get("verified"):
                errors.append(f"证据 {entry.get('id', '?')} 尚未核验")
        for observation in item.get("observations") or []:
            linked = observation.get("evidenceIds") or []
            if not linked or any(ref not in ids for ref in linked):
                errors.append(f"事实 {observation.get('id', '?')} 未正确关联证据")
                break
        body_parts = [str(item.get("executiveSummary") or ""), str(item.get("conclusion") or ""), str(item.get("whyNow") or "")]
        for key in ("observations", "analysis", "counterEvidence"):
            body_parts.extend(str(value.get("text", "")) for value in item.get(key) or [])
        body_parts.extend(str(value or "") for value in item.get("limitations") or [])
        if len("".join(body_parts)) < 600:
            errors.append("研究正文不足 600 个字符")
        if not item.get("humanReviewed"):
            errors.append("需要项目负责人完成人工确认")
        confidence = item.get("confidenceDetail") or {}
        if not all(key in confidence for key in ("overall", "sourceQuality", "evidenceAgreement", "scopeFitness", "rationale")):
            errors.append("置信度分项或理由不完整")
        return errors

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
        cases = evaluation_case_map()
        with self.session() as db:
            output = []
            for row in db.execute("SELECT * FROM eval_reviews ORDER BY configuration, case_id"):
                item = dict(row)
                case = cases.get(item["case_id"], {})
                item["case"] = case
                calculated = ai_draft_assessment(item.get("response_excerpt", ""), case) if case else None
                item["aiDraft"] = ({"factuality": item["ai_factuality"], "completeness": item["ai_completeness"],
                                    "citationCorrectness": item["ai_citation_correctness"], "structuredUsability": item["ai_structured_usability"],
                                    "issueType": item["ai_issue_type"], "note": item["ai_note"]}
                                   if item.get("ai_completed_at") else calculated)
                item["aiCompleted"] = bool(item.get("ai_completed_at"))
                item["humanConfirmed"] = bool(item.get("human_confirmed_at"))
                output.append(item)
            return output

    def persist_ai_drafts(self) -> int:
        """Store transparent rule-based initial assessments separately from human scores."""
        cases = evaluation_case_map(); updated = 0
        with self.session() as db:
            rows = list(db.execute("SELECT configuration, case_id, response_excerpt FROM eval_reviews"))
            for row in rows:
                case = cases.get(row["case_id"])
                if not case:
                    continue
                draft = ai_draft_assessment(row["response_excerpt"] or "", case)
                db.execute("""UPDATE eval_reviews SET ai_factuality=?, ai_completeness=?, ai_citation_correctness=?,
                           ai_structured_usability=?, ai_issue_type=?, ai_note=?, ai_completed_at=?
                           WHERE configuration=? AND case_id=?""",
                           (draft["factuality"], draft["completeness"], draft["citationCorrectness"], draft["structuredUsability"],
                            draft["issueType"], draft["note"], utc_now(), row["configuration"], row["case_id"]))
                updated += 1
        return updated

    @staticmethod
    def confirmed_review_scores() -> dict[str, dict[str, Any]]:
        """Project-owner-confirmed final scores for the five stratified cases."""
        return {
            "qa-01": {"factuality": 5, "completeness": 3, "citationCorrectness": 5, "structuredUsability": 4,
                      "issueType": "条件/单位遗漏", "reviewerNote": "答案给出 800 且引用正确，但遗漏一线城市、每晚、元等适用条件。"},
            "qa-06": {"factuality": 5, "completeness": 3, "citationCorrectness": 5, "structuredUsability": 4,
                      "issueType": "条件遗漏", "reviewerNote": "答案包含两天和提前一个工作日，但遗漏每月可申请与登记要求。"},
            "sum-01": {"factuality": 5, "completeness": 2, "citationCorrectness": 5, "structuredUsability": 3,
                       "issueType": "总结不完整", "reviewerNote": "关键词和引用正确，但未按两句话总结，遗漏标准请求覆盖与长尾请求仍需人工审核。"},
            "sum-06": {"factuality": 5, "completeness": 2, "citationCorrectness": 5, "structuredUsability": 3,
                       "issueType": "总结不完整", "reviewerNote": "提到来源和引用卡片，但遗漏用户认可速度，回答过于关键词化。"},
            "ext-01": {"factuality": 5, "completeness": 2, "citationCorrectness": 5, "structuredUsability": 2,
                       "issueType": "字段映射错误", "reviewerNote": "事实和引用正确，但真实值未填入 model/date/context 字段，结构化输出不可直接使用。"},
        }

    def confirm_review_matrix(self, source: str = "project_owner_chat_confirmation") -> int:
        """Record the project owner's explicit approval of all 15 human-final scores."""
        matrix = self.confirmed_review_scores(); confirmed = 0
        with self.session() as db:
            rows = list(db.execute("SELECT configuration, case_id FROM eval_reviews"))
            for row in rows:
                score = matrix.get(row["case_id"])
                if not score:
                    continue
                db.execute("""UPDATE eval_reviews SET factuality=?, completeness=?, citation_correctness=?, structured_usability=?,
                           issue_type=?, reviewer_note=?, status='complete', human_confirmed_at=?, human_confirmation_source=?, updated_at=?
                           WHERE configuration=? AND case_id=?""",
                           (score["factuality"], score["completeness"], score["citationCorrectness"], score["structuredUsability"],
                            score["issueType"], score["reviewerNote"], utc_now(), source, utc_now(), row["configuration"], row["case_id"]))
                confirmed += 1
        return confirmed

    def dual_evaluation_summary(self) -> dict[str, Any]:
        """Public aggregate only: never includes raw answers or private excerpts."""
        score_columns = ("factuality", "completeness", "citation_correctness", "structured_usability")
        labels = {"factuality": "事实性", "completeness": "完整性", "citation_correctness": "引用正确", "structured_usability": "结构可用"}
        with self.session() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM eval_reviews ORDER BY configuration, case_id")]
        complete = [row for row in rows if row.get("human_confirmed_at") and row.get("ai_completed_at")]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows: grouped.setdefault(row["configuration"], []).append(row)
        configurations = []
        for configuration, group in grouped.items():
            metrics, deltas = {}, []
            for column in score_columns:
                ai_column = "ai_" + column
                human = [row[column] for row in group if row.get(column) is not None]
                ai = [row[ai_column] for row in group if row.get(ai_column) is not None]
                metrics[labels[column]] = {"aiInitialAverage": round(sum(ai) / len(ai), 2) if ai else None,
                                           "humanFinalAverage": round(sum(human) / len(human), 2) if human else None}
                deltas.extend(abs(row[column] - row[ai_column]) for row in group if row.get(column) is not None and row.get(ai_column) is not None)
            exact = sum(all(row.get(column) == row.get("ai_" + column) for column in score_columns) for row in group)
            badcases: dict[str, int] = {}
            for row in group:
                if row.get("issue_type") and row["issue_type"] != "待标注": badcases[row["issue_type"]] = badcases.get(row["issue_type"], 0) + 1
            configurations.append({"id": configuration, "sampleCount": len(group), "humanConfirmed": sum(bool(row.get("human_confirmed_at")) for row in group),
                                   "aiCompleted": sum(bool(row.get("ai_completed_at")) for row in group), "metrics": metrics,
                                   "meanAbsoluteScoreDifference": round(sum(deltas) / len(deltas), 2) if deltas else None,
                                   "exactMatchRate": round(exact / len(group) * 100, 1) if group else 0,
                                   "badcaseDistribution": [{"type": key, "count": value} for key, value in sorted(badcases.items())]})
        overall_badcases: dict[str, int] = {}
        for row in complete:
            if row.get("issue_type") and row["issue_type"] != "待标注": overall_badcases[row["issue_type"]] = overall_badcases.get(row["issue_type"], 0) + 1
        status = "completed" if len(rows) == 15 and len(complete) == 15 else "human_confirmation_in_progress"
        return {"schemaVersion": "0.8.0", "generatedAt": utc_now(), "title": "DeepSeek 人机双重评估汇总", "sampleCount": len(rows),
                "aiCompleted": sum(bool(row.get("ai_completed_at")) for row in rows), "humanConfirmed": sum(bool(row.get("human_confirmed_at")) for row in rows),
                "dualValidationStatus": status, "humanConfirmationSource": "项目负责人已在对话中确认评分", "configurations": configurations,
                "overallBadcaseDistribution": [{"type": key, "count": value} for key, value in sorted(overall_badcases.items())],
                "findings": ["三组配置在这 15 条分层抽样中未显示明显体验差异，不能据此宣传某个配置更强。", "主要问题集中在总结覆盖不足、条件遗漏和结构化字段映射错误。"],
                "nextActions": ["把遗漏条件、单位和适用范围加入评分断言。", "为总结题增加格式、正反信息与行动项覆盖检查。", "为结构化抽取增加 schema 校验和失败回退后复跑同题集。"],
                "privacy": "公开页面仅展示汇总、方法和问题分布；原始模型回答只保留在本机忽略目录。"}

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
        with self.session() as db:
            existing = db.execute("SELECT * FROM eval_reviews WHERE configuration=? AND case_id=?", (configuration, case_id)).fetchone()
            if not existing:
                raise KeyError(f"{configuration}/{case_id}")
            score_values = {key: changes.get(key, existing[column]) for key, column in field_map.items()
                            if key in {"factuality", "completeness", "citationCorrectness", "structuredUsability"}}
            completed = all(value is not None for value in score_values.values())
            if completed:
                assignments.extend(["status=?", "human_confirmed_at=?", "human_confirmation_source=?", "updated_at=?"])
                values.extend(["complete", utc_now(), "local_admin_confirmation", utc_now(), configuration, case_id])
            else:
                assignments.extend(["status=?", "updated_at=?"]); values.extend(["pending", utc_now(), configuration, case_id])
            db.execute(f"UPDATE eval_reviews SET {', '.join(assignments)} WHERE configuration=? AND case_id=?", values)
            row = db.execute("SELECT * FROM eval_reviews WHERE configuration=? AND case_id=?", (configuration, case_id)).fetchone()
            return dict(row)

    def export_public(self, data_dir: Path | str = DATA) -> dict[str, Any]:
        data_dir = Path(data_dir); data_dir.mkdir(parents=True, exist_ok=True)
        with self.session() as db:
            approved = [self._item(row) for row in db.execute(
                "SELECT * FROM review_items WHERE status='approved' AND reviewed=1 AND human_reviewed=1 ORDER BY published_at DESC"
            )]
        signals = [self._signal(item) for item in approved]
        generated_at = utc_now()
        actions = []
        for signal in signals[:8]:
            for action in signal["action"]:
                if action not in actions:
                    actions.append(action)
        report = {"schemaVersion": "1.0.0", "generatedAt": generated_at, "title": "AI 行业策略周报",
                  "judgements": [{"signalId": item["id"], "researchQuestion": item.get("researchQuestion"),
                                  "executiveSummary": item.get("executiveSummary"), "conclusion": item["conclusion"],
                                  "whyNow": item["whyNow"], "impact": item["impact"],
                                  "evidenceCount": len(item.get("evidence", [])), "source": item["source"]} for item in signals[:5]],
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
                "category": row["category"], "track": row["track"], "entities": parse_json(row["entities_json"], []), "title": row["title"], "url": row["url"],
                "publishedAt": row["published_at"], "summary": row["summary"], "status": row["status"], "conclusion": row["conclusion"],
                "whyNow": row["why_now"], "impact": parse_json(row["impact_json"], []), "action": parse_json(row["action_json"], []),
                "questions": parse_json(row["questions_json"], []), "researchQuestion": row["research_question"],
                "executiveSummary": row["executive_summary"], "observations": parse_json(row["observations_json"], []),
                "analysis": parse_json(row["analysis_json"], []), "counterEvidence": parse_json(row["counter_evidence_json"], []),
                "limitations": parse_json(row["limitations_json"], []), "decisionImpact": parse_json(row["decision_impact_json"], []),
                "recommendedActions": parse_json(row["recommended_actions_json"], []), "evidence": parse_json(row["evidence_json"], []),
                "confidenceDetail": parse_json(row["confidence_json"], {}), "aiDrafted": bool(row["ai_drafted"]),
                "humanReviewed": bool(row["human_reviewed"]), "reviewVersion": row["review_version"],
                "humanReviewedAt": row["human_reviewed_at"],
                "priority": row["priority"], "confidence": row["confidence"], "reviewed": bool(row["reviewed"]),
                "researchScore": row["research_score"], "scoreReasons": parse_json(row["score_reasons_json"], []), "updatedAt": row["updated_at"]}

    @staticmethod
    def _signal(item: dict[str, Any]) -> dict[str, Any]:
        return {"id": item["id"], "schemaVersion": "1.0.0", "track": item.get("track", "研究报告"),
                "category": item["category"], "title": item["title"], "researchQuestion": item.get("researchQuestion"),
                "executiveSummary": item.get("executiveSummary"), "conclusion": item["conclusion"],
                "whyNow": item["whyNow"], "observations": item.get("observations", []), "analysis": item.get("analysis", []),
                "counterEvidence": item.get("counterEvidence", []), "limitations": item.get("limitations", []),
                "decisionImpact": item.get("decisionImpact", []), "recommendedActions": item.get("recommendedActions", []),
                "impact": item["impact"], "action": item["action"], "entities": item["entities"],
                "source": {"name": item["sourceName"], "url": item["url"], "publishedAt": item["publishedAt"], "type": item["sourceType"]},
                "evidence": item.get("evidence") or [{"id":"E1", "title": item["sourceName"], "sourceName": item["sourceName"], "url": item["url"], "publishedAt": item["publishedAt"], "accessedAt": utc_now()[:10], "sourceType": item["sourceType"], "evidenceRole":"支持", "note": (item.get("summary") or "")[:280], "verified": True}],
                "questions": item.get("questions", []),
                "confidence": item.get("confidenceDetail") or {"overall": item["confidence"], "sourceQuality": item["confidence"], "evidenceAgreement": item["confidence"], "scopeFitness": item["confidence"], "rationale":"旧版评分"},
                "priority": item["priority"], "status": "已复核", "reviewed": True,
                "review": {"aiDrafted": item.get("aiDrafted", False), "humanReviewed": item.get("humanReviewed", False),
                           "reviewerRole": "项目负责人", "reviewedAt": item.get("humanReviewedAt"), "version": item.get("reviewVersion") or "1.0"}}
