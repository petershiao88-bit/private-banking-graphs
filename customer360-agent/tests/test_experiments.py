"""實驗的守門測試：程式版與 SHACL 版檢查器必須等價；錯誤注入的攔截率不能退步。"""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import common  # noqa: E402
from c360_agent import plan as planning  # noqa: E402


class ShaclEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from shacl_gate import ShaclGate
        cls.kb = common.kb()
        cls.sg = ShaclGate(cls.kb)

    def test_code_and_shacl_agree_on_sample(self):
        cases = common.apply_faults(question_file="holdout2.yaml")[::3]  # 抽樣，控制測試時間
        cases += [{"question": q, "plan": common.gold_plan(q)} for q in common.questions("holdout2.yaml")[::4]]
        for c in cases:
            q, plan = c["question"], c["plan"]
            code = planning.Gate(self.kb, q["role"]).check(plan, q["question"])
            sh = self.sg.check(plan, q["question"], q["role"])
            shacl_hard = set(sh["hard"]) - ({"unknown_metric"} if "gap_metric" in sh["hard"] else set())
            self.assertEqual(sorted({e["code"] for e in code["errors"]}), sorted(shacl_hard), (q["id"], c.get("fault")))
            self.assertEqual(sorted({e["code"] for e in code["challenges"]}), sh["soft"], (q["id"], c.get("fault")))


class FaultDetectionRegressionTest(unittest.TestCase):
    def test_detection_floor(self):
        """調參集：硬擋至少 60%、加上質疑 100%；正確計畫零硬擋。"""
        kb = common.kb()
        cases = common.apply_faults()
        wrong = hard = flagged = 0
        for c in cases:
            q, plan = c["question"], c["plan"]
            verdict = common.evaluate.score(q, {"decision": plan["decision"], "metrics": plan["metrics"], "plan": plan,
                                                "answer": "重複 待定 工具 持有 fh:holds 不是"}, kb)
            if verdict["outcome"] == "correct":
                continue
            wrong += 1
            r = planning.Gate(kb, q["role"]).check(plan, q["question"])
            hard += bool(r["errors"])
            flagged += bool(r["errors"] or r["challenges"])
        self.assertGreaterEqual(hard / wrong, 0.60)
        self.assertEqual(flagged, wrong)


if __name__ == "__main__":
    unittest.main()
