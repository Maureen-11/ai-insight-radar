from __future__ import annotations

import json


def evaluate_business_output(output: str, context):
    variables = context.get("vars", {})
    lower = (output or "").lower()
    keywords = variables.get("expectedKeywords", [])
    citations = variables.get("expectedCitations", [])
    required = variables.get("requiredFields", [])
    keyword_score = sum(str(value).lower() in lower for value in keywords) / max(1, len(keywords))
    citation_score = sum(str(value).lower() in lower for value in citations) / max(1, len(citations))
    try:
        parsed = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        parsed = None
    json_score = float(parsed is not None)
    schema_score = float(not required or (isinstance(parsed, dict) and all(field in parsed for field in required)))
    score = round(0.45 * keyword_score + 0.25 * citation_score + 0.15 * json_score + 0.15 * schema_score, 4)
    failures = []
    if keyword_score < 1:
        failures.append("关键信息遗漏")
    if citation_score < 1:
        failures.append("引用错误或遗漏")
    if not json_score:
        failures.append("格式错误")
    if not schema_score:
        failures.append("必填字段遗漏")
    return {
        "pass": score >= 0.7,
        "score": score,
        "reason": "通过确定性检查" if not failures else "；".join(failures),
        "namedScores": {"keywords": keyword_score, "citations": citation_score, "json": json_score, "schema": schema_score},
    }

