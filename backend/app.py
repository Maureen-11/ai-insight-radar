from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .store import DATA, ROOT, ResearchStore
from scripts.generate_publication import generate as generate_publication

store = ResearchStore()
app = FastAPI(title="AI Insight Radar Research API", version="1.0.0")
STATIC = Path(__file__).parent / "static"
app.mount("/admin-assets", StaticFiles(directory=STATIC), name="admin-assets")


def export_all() -> dict[str, Any]:
    exported = store.export_public(DATA)
    signals = json.loads((DATA / "signals.json").read_text(encoding="utf-8"))
    publication = generate_publication(signals, DATA, ROOT / "reports", datetime.now(timezone.utc))
    return {**exported, "publication": publication}


class ReviewUpdate(BaseModel):
    status: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    category: str | None = None
    title: str | None = None
    url: str | None = None
    published_at: str | None = None
    summary: str | None = None
    conclusion: str | None = None
    why_now: str | None = None
    impact: list[str] | None = None
    action: list[str] | None = None
    questions: list[str] | None = None
    entities: list[str] | None = None
    priority: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    research_question: str | None = None
    executive_summary: str | None = None
    observations: list[dict[str, Any]] | None = None
    analysis: list[dict[str, Any]] | None = None
    counter_evidence: list[dict[str, Any]] | None = None
    limitations: list[str] | None = None
    decision_impact: list[dict[str, Any]] | None = None
    recommended_actions: list[dict[str, Any]] | None = None
    evidence: list[dict[str, Any]] | None = None
    confidence_detail: dict[str, Any] | None = None
    ai_drafted: bool | None = None
    human_reviewed: bool | None = None
    review_version: str | None = None


class EvalReviewUpdate(BaseModel):
    factuality: int | None = Field(default=None, ge=1, le=5)
    completeness: int | None = Field(default=None, ge=1, le=5)
    citationCorrectness: int | None = Field(default=None, ge=1, le=5)
    structuredUsability: int | None = Field(default=None, ge=1, le=5)
    issueType: str | None = None
    reviewerNote: str | None = None


@app.on_event("startup")
def startup() -> None:
    store.initialize()
    store.bootstrap()
    store.import_eval_data()
    store.persist_ai_drafts()
    store.import_page_changes()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": app.title, "admin": "/admin", "docs": "/docs"}


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC / "admin.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "summary": store.summary()}


@app.post("/api/bootstrap")
def bootstrap() -> dict[str, int]:
    return store.bootstrap()


@app.get("/api/review/items")
def review_items(status: str = "pending", limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), query: str = "") -> list[dict[str, Any]]:
    return store.list_items(status=status, limit=limit, offset=offset, query=query)


@app.get("/api/review/items/{item_id}")
def review_item(item_id: str) -> dict[str, Any]:
    item = store.get_item(item_id)
    if not item:
        raise HTTPException(404, "item not found")
    return item


@app.patch("/api/review/items/{item_id}")
def update_review_item(item_id: str, update: ReviewUpdate) -> dict[str, Any]:
    try:
        return store.update_item(item_id, update.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(404, "item not found")
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.post("/api/review/items/{item_id}/publish")
def publish_review_item(item_id: str) -> dict[str, Any]:
    try:
        item = store.publish_item(item_id)
        export = export_all()
        return {"item": item, "export": export}
    except KeyError:
        raise HTTPException(404, "item not found")
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.post("/api/export")
def export_public() -> dict[str, Any]:
    return export_all()


@app.get("/api/auto-brief")
def auto_brief() -> dict[str, Any]:
    path = DATA / "auto-brief.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "missing", "items": []}


@app.post("/api/auto-brief/items/{item_id}/promote")
def promote_auto_brief(item_id: str) -> dict[str, Any]:
    try:
        return store.promote_auto_brief(item_id)
    except KeyError:
        raise HTTPException(404, "automatic brief item not found")


@app.get("/api/page-changes")
def page_changes(limit: int = Query(100, ge=1, le=200)) -> list[dict[str, Any]]:
    return store.list_page_changes(limit)


@app.get("/api/evaluations/reviews")
def evaluation_reviews() -> list[dict[str, Any]]:
    return store.list_eval_reviews()


@app.get("/api/evaluations/summary")
def evaluation_summary() -> dict[str, Any]:
    return store.dual_evaluation_summary()


@app.patch("/api/evaluations/reviews/{configuration}/{case_id}")
def update_evaluation_review(configuration: str, case_id: str, update: EvalReviewUpdate) -> dict[str, Any]:
    try:
        return store.update_eval_review(configuration, case_id, update.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(404, "review sample not found")
    except ValueError as error:
        raise HTTPException(422, str(error))
