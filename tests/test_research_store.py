import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.store import ResearchStore, research_score


def item(item_id="one", url="https://example.com/one"):
    return {"id": item_id, "sourceId": "official", "sourceName": "Official", "sourceType": "厂商官方",
            "category": "模型", "entities": ["Vendor"], "title": "Model API release", "url": url,
            "publishedAt": "2026-09-03T00:00:00Z", "summary": "API model pricing release",
            "draftConclusion": "需要验证", "draftImpact": ["影响采购"], "draftAction": ["运行评测"]}


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
        self.store.update_item("one", {"source_name": "Vendor release note", "why_now": "版本刚发布", "conclusion": "应重新评测", "impact": ["影响采购"], "action": ["复跑题集"], "questions": ["是否影响旧接口？"]})
        published = self.store.publish_item("one")
        self.assertTrue(published["reviewed"])
        out = self.root / "public"
        result = self.store.export_public(out)
        self.assertEqual(result["signals"], 1)
        exported = json.loads((out / "signals.json").read_text(encoding="utf-8"))
        self.assertTrue(exported[0]["reviewed"])
        self.assertEqual(exported[0]["questions"], ["是否影响旧接口？"])
        self.assertEqual(exported[0]["evidence"][0]["label"], "Vendor release note")
        self.assertTrue(exported[0]["evidence"][0]["note"])

    def test_review_state_transitions(self):
        self.store.import_items([item()])
        self.assertEqual(self.store.update_item("one", {"status": "needs_verification"})["status"], "needs_verification")
        self.assertEqual(self.store.update_item("one", {"status": "returned"})["status"], "returned")
        self.assertEqual(self.store.update_item("one", {"status": "ignored"})["status"], "ignored")


if __name__ == "__main__":
    unittest.main()
