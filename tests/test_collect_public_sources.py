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
            self.assertTrue(0 <= signal["confidence"] <= 1)

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
