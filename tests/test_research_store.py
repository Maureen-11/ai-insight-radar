import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.store import ResearchStore, ai_draft_assessment, research_score


def item(item_id="one", url="https://example.com/one"):
    return {"id": item_id, "sourceId": "official", "sourceName": "Official", "sourceType": "厂商官方",
            "category": "模型", "entities": ["Vendor"], "title": "Model API release", "url": url,
            "publishedAt": "2026-09-03T00:00:00Z", "summary": "API model pricing release",
            "draftConclusion": "需要验证", "draftImpact": ["影响采购"], "draftAction": ["运行评测"]}


def deep_report_changes():
    long_text = "这一段用于验证研究报告正文深度，说明事实、推理、产品影响与适用边界不能混为一谈。" * 16
    evidence = [
        {"id": "E1", "title": "Vendor release note", "url": "https://example.com/e1", "publishedAt": "2026-09-01",
         "accessedAt": "2026-09-03", "sourceType": "厂商官方", "evidenceRole": "支持", "verified": True},
        {"id": "E2", "title": "Independent benchmark", "url": "https://example.org/e2", "publishedAt": "2026-09-02",
         "accessedAt": "2026-09-03", "sourceType": "公开基准", "evidenceRole": "限制", "verified": True},
    ]
    return {
        "source_name": "Vendor release note", "source_type": "厂商官方", "published_at": "2026-09-01",
        "research_question": "如何形成可验证的产品判断？", "executive_summary": "证据必须先于结论。",
        "why_now": "版本刚发布", "conclusion": long_text,
        "observations": [{"id": "O1", "text": "厂商发布了新版本。", "evidenceIds": ["E1"]}],
        "analysis": [{"id": "A1", "text": long_text, "evidenceIds": ["E1", "E2"]}],
        "counter_evidence": [{"id": "C1", "text": "公开基准不能直接代表企业场景。", "evidenceIds": ["E2"]}],
        "limitations": ["尚未覆盖真实企业私有数据。"],
        "decision_impact": [{"audience": "产品", "impact": "调整选型表"}],
        "recommended_actions": [{"action": "复跑题集", "ownerRole": "评测负责人", "metric": "任务成功率", "expectedOutcome": "形成同题可比记录"}],
        "evidence": evidence, "impact": ["影响采购"], "action": ["复跑题集"], "questions": ["是否影响旧接口？"],
        "confidence": 0.75,
        "confidence_detail": {"overall": 0.75, "sourceQuality": 0.8, "evidenceAgreement": 0.7, "scopeFitness": 0.65, "rationale": "一手资料完整，但场景覆盖有限。"},
        "ai_drafted": True, "human_reviewed": False, "review_version": "1.0-draft",
    }


class ResearchStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ResearchStore(self.root / "research.db")
        self.store.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def test_import_deduplicates_by_url(self):
        self.assertEqual(self.store.import_items([item(), item("two")]), 1)
        self.assertEqual(self.store.summary()["total"], 1)

    def test_score_rewards_fresh_official_source_and_penalizes_duplicates(self):
        current = datetime(2026, 9, 3, tzinfo=timezone.utc)
        base, _ = research_score(item(), 0, current)
        duplicate, _ = research_score(item(), 2, current)
        self.assertGreater(base, duplicate)

    def test_publish_requires_research_fields_then_exports_reviewed_only(self):
        self.store.import_items([item()])
        with self.assertRaises(ValueError):
            self.store.publish_item("one")
        self.store.update_item("one", deep_report_changes())
        with self.assertRaisesRegex(ValueError, "人工确认"):
            self.store.publish_item("one")
        self.store.update_item("one", {"human_reviewed": True, "review_version": "1.0"})
        published = self.store.publish_item("one")
        self.assertTrue(published["reviewed"])
        self.assertTrue(published["humanReviewed"])
        out = self.root / "public"
        result = self.store.export_public(out)
        self.assertEqual(result["signals"], 1)
        exported = json.loads((out / "signals.json").read_text(encoding="utf-8"))
        self.assertTrue(exported[0]["reviewed"])
        self.assertEqual(exported[0]["questions"], ["是否影响旧接口？"])
        self.assertEqual(exported[0]["evidence"][0]["title"], "Vendor release note")
        self.assertEqual(exported[0]["schemaVersion"], "1.0.0")
        self.assertTrue(exported[0]["review"]["humanReviewed"])

    def test_auto_brief_promotion_stays_pending(self):
        brief = self.root / "auto-brief.json"
        brief.write_text(json.dumps({"items": [{"id": "auto-1", "title": "New model", "summary": "摘要",
            "whatChanged": "出现新版本", "impact": ["需要观察"], "action": ["核对文档"],
            "source": {"name": "Official", "url": "https://example.com/new", "publishedAt": "2026-09-03", "type": "厂商官方"}}]}), encoding="utf-8")
        promoted = self.store.promote_auto_brief("auto-1", brief)
        self.assertEqual(promoted["status"], "pending")
        self.assertFalse(promoted["reviewed"])
        self.assertFalse(promoted["humanReviewed"])

    def test_review_state_transitions(self):
        self.store.import_items([item()])
        self.assertEqual(self.store.update_item("one", {"status": "needs_verification"})["status"], "needs_verification")
        self.assertEqual(self.store.update_item("one", {"status": "returned"})["status"], "returned")
        self.assertEqual(self.store.update_item("one", {"status": "ignored"})["status"], "ignored")

    def test_ai_draft_flags_wrong_structured_field_mapping(self):
        case = {"keywords": ["Atlas-1", "2026-08-01", "128K"], "citations": ["DOC-E1"], "required_fields": ["model", "date", "context"]}
        response = '{"answer":"Atlas-1；2026-08-01；128K","citations":["DOC-E1"],"model":"已提取","date":"已提取","context":"已提取"}'
        draft = ai_draft_assessment(response, case)
        self.assertEqual(draft["factuality"], 5)
        self.assertEqual(draft["structuredUsability"], 2)
        self.assertEqual(draft["issueType"], "字段映射错误")

    def test_dual_review_summary_separates_ai_and_human_and_hides_response(self):
        responses = self.root / "responses.json"
        responses.write_text(json.dumps([
            {"configuration": configuration, "caseId": case, "response": '{"answer":"private raw answer"}'}
            for configuration in ("flash-direct", "flash-thinking", "pro-thinking")
            for case in ("qa-01", "qa-06", "sum-01", "sum-06", "ext-01")
        ]), encoding="utf-8")
        review = self.root / "review.json"
        review.write_text(json.dumps({"samples": [
            {"configuration": configuration, "caseId": case}
            for configuration in ("flash-direct", "flash-thinking", "pro-thinking")
            for case in ("qa-01", "qa-06", "sum-01", "sum-06", "ext-01")
        ]}), encoding="utf-8")
        self.store.import_eval_data(review_path=review, responses_path=responses, results_path=self.root / "missing.json")
        self.assertEqual(self.store.persist_ai_drafts(), 15)
        self.assertEqual(self.store.confirm_review_matrix(), 15)
        summary = self.store.dual_evaluation_summary()
        self.assertEqual(summary["dualValidationStatus"], "completed")
        self.assertEqual(summary["humanConfirmed"], 15)
        self.assertEqual(len(summary["configurations"]), 3)
        self.assertNotIn("response_excerpt", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
