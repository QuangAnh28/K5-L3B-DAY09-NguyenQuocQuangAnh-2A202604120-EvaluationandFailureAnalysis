"""Regression checks for first wrong decisions, missing evidence and honest wording changes."""
import copy
import math
import pytest
from lab9 import gate, stats
from lab9.graders import ReplyAmountConsistent
from lab9.trace_case import investigate
from types import SimpleNamespace

pytestmark = pytest.mark.student


def test_lab9_first_wrong_decision_and_fixed_control():
    bad = investigate("seeded_regression", "C-002", 11)["trial"]
    good = investigate("fixed", "C-002", 11)["trial"]
    assert bad["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert not bad["lab8_pass"] and bad["snapshot"]["refund_vnd"] == 20000
    assert good["lab8_pass"] and good["snapshot"]["refund_vnd"] == 0
    assert not any(e["kind"] == "model_override" for e in good["events"])


@pytest.mark.parametrize("text,amount,expected", [
    ("Dạ, LogiX đã hoàn 35.000đ cho đơn O-107.", 35000, True),
    ("LogiX đã hoàn phí 35,000 VND cho đơn O-107 ạ.", 35000, True),
    ("Đã hoàn 35000 đồng.", 20000, False),
    ("Đã hoàn 35.000đ.", 0, False),
    ("Chưa đủ điều kiện hoàn.", 0, True),
])
def test_lab9_reply_money_is_independent_of_paraphrase(text, amount, expected):
    ctx = SimpleNamespace(output={"events": [{"kind": "reply", "payload": {"text": text}}],
                                  "snapshot": {"refund_vnd": amount}, "result": {}})
    assert ReplyAmountConsistent().evaluate(ctx).value is expected


def report():
    return {"manifest": {"eval_set_sha": "x", "items": 2, "seeds": [11, 22]},
            "metrics": {"pass_rate": 1.0}, "evaluator_failures": [],
            "rows": [{"item_id": i, "seed": seed, "pass_rate": True, "slices": ["money_movement"]}
                     for i in ("a", "b") for seed in (11, 22)]}

SPEC = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "blocking": True,
         "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.9,
                    "blocking": True, "no_significant_drop": True}]}


@pytest.mark.parametrize("corrupt", ["duplicate", "failure", "none", "infinity", "seed", "slice", "aggregate"])
def test_lab9_advanced_integrity_checks_raw_evidence(corrupt):
    base = report(); pr = copy.deepcopy(base)
    if corrupt == "duplicate": pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    if corrupt == "failure": pr["evaluator_failures"] = ["crashed on green row"]
    if corrupt == "none": pr["rows"][0]["pass_rate"] = None
    if corrupt == "infinity": pr["metrics"]["pass_rate"] = math.inf
    if corrupt == "seed": pr["rows"][0]["seed"] = 99
    if corrupt == "slice": pr["rows"][0]["slices"] = []
    if corrupt == "aggregate": pr["metrics"]["pass_rate"] = 0.95
    assert gate.check(pr, base, SPEC)[0] == ["integrity"]
    assert gate.check(base, base, SPEC)[0] == []


@pytest.mark.parametrize("change", ["drop_metric", "unblock", "drop_ci", "drop_slice", "slice_floor"])
def test_lab9_advanced_ratchet(change):
    old = copy.deepcopy(SPEC); new = copy.deepcopy(old)
    if change == "drop_metric": new["metrics"] = []
    if change == "unblock": new["metrics"][0]["blocking"] = False
    if change == "drop_ci": new["metrics"][0]["threshold"].pop("no_significant_drop")
    if change == "drop_slice": new["slices"] = []
    if change == "slice_floor": new["slices"][0]["min"] = 0.5
    assert gate.integrity_check(report(), report(), new, old)


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0), (5, 2, 6), (5.0, 2, 1), (True, 0, 1)])
def test_lab9_advanced_both_estimators_reject_invalid_counts(args):
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError): fn(*args)


def test_lab9_advanced_quiet_override_caught_without_event(tmp_path):
    import json
    from lab8.shapes import SHAPES
    from lab9.eval import load_spec, load_world, make_task
    from lab9.variant_agent import make_shape
    from lab9.graders import RefundAmountCorrect, DbFactKept
    spec = load_spec()
    world, claims = load_world(spec)
    labels = json.loads(open(spec["labels"], encoding="utf-8").read())
    SHAPES["test_quiet"] = make_shape("test_quiet", {"no_override", "quiet_override"})
    trial = make_task("test_quiet", world, claims, labels, tmp_path)({"claim_id": "C-002", "seed": 11})
    ctx = SimpleNamespace(output=trial, expected_output=labels["C-002"])
    assert DbFactKept().evaluate(ctx).value is True
    assert RefundAmountCorrect().evaluate(ctx).value is False
    assert not trial["lab8_pass"]


def test_lab9_misreport_is_caught_when_lab8_passes(tmp_path):
    import json
    from lab8.shapes import SHAPES
    from lab9.eval import load_spec, load_world, make_task
    from lab9.variant_agent import make_shape
    spec = load_spec(); world, claims = load_world(spec)
    labels = json.loads(open(spec["labels"], encoding="utf-8").read())
    SHAPES["test_misreport"] = make_shape("test_misreport", {"no_override", "misreport"})
    trial = make_task("test_misreport", world, claims, labels, tmp_path)({"claim_id": "C-008", "seed": 11})
    assert trial["lab8_pass"]
    assert ReplyAmountConsistent().evaluate(SimpleNamespace(output=trial)).value is False


def test_lab9_constant_judge_fails_calibration_without_crashing(tmp_path):
    from lab9.judge import calibrate
    csv = tmp_path / "constant.csv"
    csv.write_text("item_id,reply,human,judge\na,ok,PASS,PASS\nb,ok,PASS,PASS\n", encoding="utf-8")
    result = calibrate(csv)
    assert not result["passed"]
    assert math.isnan(result["kappa"])
    assert result["corrected_fail_rate"] is None


def test_lab9_evalset_uses_canonical_lf_bytes(tmp_path, monkeypatch):
    import json
    from lab9 import evalset
    source = tmp_path / "public.jsonl"
    source.write_text(json.dumps({"claim_id": "C-001", "matrix_id": "T01", "expected": {"refund_vnd": 35000}}) + "\n", encoding="utf-8")
    monkeypatch.setattr(evalset, "ITEMS", tmp_path / "items.jsonl")
    monkeypatch.setattr(evalset, "LABELS", tmp_path / "labels.json")
    evalset.build(source)
    assert b"\r\n" not in evalset.ITEMS.read_bytes()
    assert b"\r\n" not in evalset.LABELS.read_bytes()
    assert evalset.ITEMS.read_bytes().endswith(b"\n")


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), "0.5", True, None])
@pytest.mark.parametrize("section,bound", [("metrics", "min"), ("metrics", "max"),
                                           ("metrics", "max_increase"), ("slices", "min")])
def test_lab9_advanced_nonfinite_or_nonnumeric_spec_is_blocked(invalid, section, bound):
    spec = copy.deepcopy(SPEC)
    target = spec[section][0]["threshold"] if section == "metrics" else spec[section][0]
    target[bound] = invalid
    assert gate.check(report(), report(), spec, SPEC)[0] == ["integrity"]


def test_lab9_advanced_version_alias_cannot_unlock_ratchet():
    loose = copy.deepcopy(SPEC)
    loose["eval_set_version"] = "v3"
    loose["metrics"][0]["threshold"] = {"min": 0.1}
    loose["slices"] = []
    assert gate.check(report(), report(), loose, SPEC)[0] == ["integrity"]


def test_lab9_advanced_version_must_match_dataset_bytes(tmp_path):
    import json
    from lab9.evalset import sha12
    data = tmp_path / "v2.jsonl"
    data.write_text("".join(json.dumps({"item_id": i, "eval_set_version": "v2"}) + "\n" for i in ("a", "b")), encoding="utf-8")
    spec = copy.deepcopy(SPEC)
    spec.update(eval_set=str(data), eval_set_version="v3")
    base = report(); base["manifest"]["eval_set_sha"] = sha12(data)
    assert gate.check(base, base, spec, SPEC)[0] == ["integrity"]


def test_lab9_advanced_genuine_new_dataset_can_start_new_floors(tmp_path):
    import json
    from lab9.evalset import sha12
    old, new = tmp_path / "v2.jsonl", tmp_path / "v3.jsonl"
    for path, version in ((old, "v2"), (new, "v3")):
        path.write_text("".join(json.dumps({"item_id": i, "eval_set_version": version}) + "\n" for i in ("a", "b")), encoding="utf-8")
    old_spec = copy.deepcopy(SPEC); old_spec["eval_set"] = str(old)
    new_spec = copy.deepcopy(SPEC)
    new_spec.update(eval_set=str(new), eval_set_version="v3")
    new_spec["metrics"][0]["threshold"]["min"] = 0.7
    base = report(); base["manifest"].update(eval_set_sha=sha12(new), eval_set_version="v3")
    assert gate.check(base, base, new_spec, old_spec)[0] == []


@pytest.mark.parametrize("text,expected", [
    ("Phí ship gốc 35.000đ; LogiX đã hoàn 20.000đ.", True),
    ("LogiX đã hoàn lại phí ship 20.000đ.", True),
    ("LogiX đã hoàn lại phí ship 35.000đ.", False),
    ("Đã được hoàn toàn bộ phí vận chuyển 20.000đ.", True),
    ("Đã được hoàn toàn bộ phí vận chuyển 35.000đ.", False),
    ("Phí ship gốc 35.000đ, LogiX đã hoàn 20.000đ.", True),
    ("LogiX đã hoàn 20.000đ trong tổng phí 35.000đ.", True),
    ("Phí ship 35.000đ, hạn mức 25.000đ; đã hoàn 20.000đ.", True),
    ("Đề xuất hoàn 35.000đ; đã hoàn 20.000đ.", True),
    ("Chưa hoàn 35.000đ; đã hoàn 20.000đ.", True),
    ("Phí ship gốc 20.000đ; LogiX đã hoàn 35.000đ.", False),
    ("LogiX đã refund 35,000 VND; phí ship 20,000 VND.", False),
    ("Da, phi ship goc 35.000 VND; LogiX da hoan 20.000 VND.", True),
])
def test_lab9_refund_assertion_is_separate_from_context_amounts(text, expected):
    ctx = SimpleNamespace(output={"events": [{"kind": "reply", "payload": {"text": text}}],
                                  "result": {}, "snapshot": {"refund_vnd": 20000}})
    assert ReplyAmountConsistent().evaluate(ctx).value is expected
