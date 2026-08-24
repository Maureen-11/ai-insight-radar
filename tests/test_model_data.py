import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))

class ModelDataTests(unittest.TestCase):
    def test_profiles_have_traceable_sources(self):
        profiles = read("models.json")
        self.assertGreaterEqual(len(profiles), 5)
        self.assertTrue(all(item["id"] and item["region"] and item["source"]["url"] for item in profiles))

    def test_evidence_does_not_mix_public_information_with_local_scores(self):
        profiles = {item["id"] for item in read("models.json")}
        evidence = read("model-evidence.json")
        self.assertTrue(all(item["modelId"] in profiles and item["source"]["url"] for item in evidence))
        self.assertTrue(all(not item["metrics"] for item in evidence if item["type"] != "local"))
        self.assertTrue(all(item["sampleCount"] > 0 for item in evidence if item["type"] == "local"))

    def test_review_template_has_all_product_quality_dimensions(self):
        review = read("model-review.json")
        self.assertEqual(review["status"], "pending")
        self.assertTrue({"factuality_1_to_5", "completeness_1_to_5", "citation_correctness_1_to_5", "structured_usability_1_to_5", "issueType"}.issubset(review["fields"]))
        self.assertGreater(len(review["samples"]), 0)

if __name__ == "__main__":
    unittest.main()
