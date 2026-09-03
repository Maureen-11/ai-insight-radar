"""Persist project-owner-confirmed human scores and write a public-safe aggregate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.store import DATA, ResearchStore


def main() -> int:
    store = ResearchStore()
    store.initialize()
    store.import_eval_data()
    ai_count = store.persist_ai_drafts()
    human_count = store.confirm_review_matrix()
    summary = store.dual_evaluation_summary()
    target = DATA / "eval-dual-review-summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"aiInitialAssessments": ai_count, "humanConfirmations": human_count,
                      "status": summary["dualValidationStatus"], "output": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
