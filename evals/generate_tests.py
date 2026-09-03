from __future__ import annotations

import json
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "data" / "eval-scenarios.json"


def generate_tests(config=None):
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    tests = []
    for scenario in dataset["scenarios"]:
        for case in scenario["cases"]:
            context = "\n".join(f"[{item['id']}] {item['text']}" for item in case["context"])
            tests.append(
                {
                    "description": f"{scenario['id']} / {case['id']}",
                    "vars": {
                        "caseId": case["id"],
                        "scenario": scenario["id"],
                        "task": case["prompt"],
                        "context": context,
                        "expectedKeywords": case.get("keywords", []),
                        "expectedCitations": case.get("citations", []),
                        "requiredFields": case.get("required_fields", []),
                    },
                }
            )
    return tests

