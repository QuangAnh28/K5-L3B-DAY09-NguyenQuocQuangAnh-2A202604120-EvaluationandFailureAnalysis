"""Reproduce the three review findings against actual reports, with fixed expected verdicts."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from lab8.console import utf8_stdio
from lab9 import gate
from lab9.eval import load_spec
from lab9.graders import ReplyAmountConsistent


def main():
    utf8_stdio()
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    base = json.loads(Path("reports/baseline_v2.json").read_text(encoding="utf-8"))
    pr = json.loads(Path("reports/eval_slice_regression_v2.json").read_text(encoding="utf-8"))
    records = []
    nan = copy.deepcopy(spec)
    for metric in nan["metrics"]:
        if "min" in metric.get("threshold", {}): metric["threshold"]["min"] = float("nan")
    for entry in nan["slices"]: entry["min"] = float("nan")
    alias = copy.deepcopy(spec)
    alias["eval_set_version"] = "v3"
    for metric in alias["metrics"]:
        if "min" in metric.get("threshold", {}): metric["threshold"]["min"] = 0
        metric.get("threshold", {}).pop("no_significant_drop", None)
    alias["slices"] = []
    for name, modified in (("nonfinite_floor", nan), ("version_alias_same_data", alias)):
        blocked, lines = gate.check(pr, base, modified, spec)
        records.append({"case": name, "expected": ["integrity"], "actual": blocked, "reasons": lines})
    texts = [("honest_context", "Phí ship gốc 35.000đ; LogiX đã hoàn 20.000đ.", True),
             ("wrong_refund", "Phí ship gốc 20.000đ; LogiX đã hoàn 35.000đ.", False)]
    for name, text, expected in texts:
        ctx = SimpleNamespace(output={"events": [{"kind": "reply", "payload": {"text": text}}],
                                      "snapshot": {"refund_vnd": 20000}, "result": {}})
        verdict = ReplyAmountConsistent().evaluate(ctx)
        records.append({"case": name, "reply": text, "ledger": 20000,
                        "expected": expected, "actual": verdict.value, "reason": verdict.reason})
    success = all(r["expected"] == r["actual"] for r in records)
    Path("reports/review_regressions.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    for record in records:
        print(record["case"], "PASS" if record["expected"] == record["actual"] else "FAIL", record["actual"])
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
