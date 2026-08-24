import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deepseek_eval", ROOT / "scripts" / "run_deepseek_eval.py")
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)

class DeepSeekEvalTests(unittest.TestCase):
    def test_public_dataset_has_thirty_cases_and_citations(self):
        dataset = runner.load(ROOT / "data" / "eval-scenarios.json")
        cases = runner.cases(dataset)
        self.assertEqual(len(cases), 30)
        self.assertTrue(all(case["citations"] and case["context"] for _, case in cases))

    def test_deterministic_score_and_schema(self):
        case = {"keywords":["Atlas","128K"],"citations":["DOC-1"],"required_fields":["model"]}
        score = runner.score(case, '{"model":"Atlas","evidence":"DOC-1","context":"128K"}')
        self.assertEqual(score["quality"], 100.0); self.assertEqual(score["schemaValid"], 1)

    def test_cost_uses_usage_fields(self):
        price={"inputCacheHit":0,"inputCacheMiss":1,"output":2}
        value=runner.cost_cny({"prompt_tokens":1000000,"completion_tokens":1000000},price,1)
        self.assertEqual(value,3)

if __name__ == "__main__": unittest.main()
