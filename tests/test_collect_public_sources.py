import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collector", ROOT / "scripts" / "collect_public_sources.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

SOURCE = {"id": "fixture", "name": "Fixture", "url": "https://example.test/feed", "type": "RSS", "category": "产品", "entities": ["Fixture"]}

class CollectorTests(unittest.TestCase):
    def test_displayed_signals_follow_minimum_contract(self):
        signals = collector.read_json(ROOT / "data" / "signals.json", [])
        required = {"id", "category", "title", "conclusion", "whyNow", "impact", "action", "entities", "source", "evidence", "confidence", "priority", "status", "reviewed"}
        self.assertGreaterEqual(len(signals), 5)
        for signal in signals:
            self.assertTrue(required.issubset(signal))
            self.assertTrue({"name", "url", "publishedAt", "type"}.issubset(signal["source"]))
            confidence = signal["confidence"]
            value = confidence.get("overall") if isinstance(confidence, dict) else confidence
            self.assertTrue(0 <= value <= 1)

    def test_v1_reports_are_deep_traceable_human_confirmed_reports(self):
        signals = collector.read_json(ROOT / "data" / "signals.json", [])
        self.assertEqual([item["id"] for item in signals], [f"signal-{number:03d}" for number in range(1, 6)])
        for signal in signals:
            self.assertEqual(signal.get("schemaVersion"), "1.0.0")
            self.assertTrue(signal["reviewed"])
            self.assertTrue(signal["review"]["humanReviewed"])
            self.assertEqual(signal["review"]["version"], "1.0.0")
            evidence = signal["evidence"]
            evidence_ids = {entry["id"] for entry in evidence}
            self.assertGreaterEqual(len(evidence), 2)
            self.assertTrue(any(any(token in entry["sourceType"] for token in ("厂商官方", "开源项目", "开源评测", "本项目")) for entry in evidence))
            for observation in signal["observations"]:
                self.assertTrue(observation["evidenceIds"])
                self.assertTrue(set(observation["evidenceIds"]).issubset(evidence_ids))
            body = [signal["executiveSummary"], signal["conclusion"], signal["whyNow"]]
            for key in ("observations", "analysis", "counterEvidence"):
                body.extend(row["text"] for row in signal[key])
            body.extend(signal["limitations"])
            self.assertGreaterEqual(len("".join(body)), 600)

    def test_parses_atom_and_strips_html(self):
        payload = (ROOT / "tests" / "fixtures" / "sample_atom.xml").read_bytes()
        items = collector.parse_feed(payload, SOURCE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://example.test/release-1")
        self.assertEqual(items[0]["summary"], "A short release note.")
        self.assertFalse(items[0]["reviewed"])

    def test_deduplicates_by_url_and_keeps_existing_on_failure(self):
        payload = (ROOT / "tests" / "fixtures" / "sample_rss.xml").read_bytes()
        first, errors = collector.collect([SOURCE], [], 1, fetcher=lambda *_: payload)
        second, errors2 = collector.collect([SOURCE], first, 1, fetcher=lambda *_: payload)
        self.assertEqual(len(first), 1); self.assertEqual(len(second), 1); self.assertEqual(errors, []); self.assertEqual(errors2, [])
        preserved, failures = collector.collect([SOURCE], first, 1, fetcher=lambda *_: (_ for _ in ()).throw(TimeoutError("timeout")))
        self.assertEqual(preserved, first); self.assertEqual(len(failures), 1)

if __name__ == "__main__":
    unittest.main()
