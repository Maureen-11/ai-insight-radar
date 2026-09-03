import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from evals.assertions import evaluate_business_output
from evals.generate_tests import generate_tests
from scripts.generate_publication import generate
from scripts.monitor_public_pages import monitor


class MonitorAndPublicationTests(unittest.TestCase):
    def test_page_monitor_creates_baseline_then_change(self):
        sources = [{"id": "vendor", "name": "Vendor", "url": "https://example.com", "kind": "page", "enabled": True}]
        first = lambda url, timeout: b"<html><body><h1>Version 1</h1></body></html>"
        snapshots, changes, health = monitor(sources, {}, first)
        self.assertEqual(changes, [])
        self.assertEqual(health[0]["status"], "ok")
        second = lambda url, timeout: b"<html><body><h1>Version 2</h1><p>New price</p></body></html>"
        _, changes, _ = monitor(sources, snapshots, second)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["status"], "待复核")

    def test_publication_excludes_unreviewed_signals(self):
        signals = [
            {"id": "approved", "reviewed": True, "priority": "high", "confidence": .9, "category": "模型", "title": "T",
             "conclusion": "C", "whyNow": "W", "impact": ["I"], "action": ["A"], "entities": ["V"],
             "source": {"name": "Official", "url": "https://example.com/a", "publishedAt": "2026-09-03"}},
            {"id": "pending", "reviewed": False, "conclusion": "Should not appear", "source": {"url": "https://example.com/b"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root / "data"; reports = root / "reports"
            result = generate(signals, output, reports, datetime(2026, 9, 3, tzinfo=timezone.utc))
            self.assertEqual(result["reviewed"], 1)
            self.assertNotIn("Should not appear", (output / "weekly-report.json").read_text(encoding="utf-8"))
            self.assertEqual((root / "feed.xml").read_text(encoding="utf-8").count("<item>"), 1)

    def test_promptfoo_generator_and_deterministic_assertion(self):
        self.assertEqual(len(generate_tests()), 30)
        context = {"vars": {"expectedKeywords": ["800"], "expectedCitations": ["DOC-Q1"], "requiredFields": ["answer", "citations"]}}
        result = evaluate_business_output('{"answer":"800","citations":["DOC-Q1"]}', context)
        self.assertTrue(result["pass"])
        self.assertEqual(result["namedScores"]["json"], 1.0)

    def test_human_review_queue_is_stratified(self):
        root = Path(__file__).resolve().parents[1]
        review = json.loads((root / "data" / "model-review.json").read_text(encoding="utf-8"))
        self.assertEqual(len(review["samples"]), 15)
        for configuration in {sample["configuration"] for sample in review["samples"]}:
            case_ids = {sample["caseId"] for sample in review["samples"] if sample["configuration"] == configuration}
            self.assertTrue(any(case.startswith("qa-") for case in case_ids))
            self.assertTrue(any(case.startswith("sum-") for case in case_ids))
            self.assertTrue(any(case.startswith("ext-") for case in case_ids))


if __name__ == "__main__":
    unittest.main()
