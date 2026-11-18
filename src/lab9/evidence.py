"""Generate reproducible trace/calibration evidence without changing Lab 8 or variants."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path
from lab8.shapes import SHAPES
from lab8.console import utf8_stdio
from lab9.eval import load_spec, load_world, make_task
from lab9.judge import calibrate
from lab9.variant_agent import make_shape
from lab9 import variants


def main():
    utf8_stdio()
    variants.register()
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    # Existing public bug switches exercised independently to locate first wrong events.
    cases = [("FM-01", "C-001", {"no_override", "leaky_trace"}),
             ("FM-02", "C-007", {"no_override", "ignore_denied"}),
             ("FM-03", "C-002", {"ticket_trust"}),
             ("FM-04", "C-014", {"no_override", "sum_parts"}),
             ("FM-05", "C-014", {"no_override", "pre_deducted"}),
             ("FM-06", "C-006", {"no_override", "stale_clause"}),
             ("FM-07", "C-001", {"no_override", "sibling_refund"}),
             ("FM-08", "C-008", {"no_override", "misreport"}),
             ("FM-09", "C-113", {"no_override"})]
    evidence = []
    with tempfile.TemporaryDirectory(prefix="lab9-evidence-", ignore_cleanup_errors=True) as tmp:
        for fm, claim, bugs in cases:
            shape = "evidence_" + fm.replace("-", "_")
            SHAPES[shape] = make_shape(shape, bugs)
            broken = make_task(shape, world, claims, labels, Path(tmp))({"claim_id": claim, "seed": 11})
            fixed = make_task("fixed", world, claims, labels, Path(tmp))({"claim_id": claim, "seed": 11})
            evidence.append({"fm": fm, "claim_id": claim, "seed": 11, "bugs": sorted(bugs),
                             "trial": broken, "fixed": fixed, "label": labels[claim]})
        for shape in ("seeded_regression", "fixed"):
            trial = make_task(shape, world, claims, labels, Path(tmp))({"claim_id": "C-002", "seed": 11})
            evidence.append({"case": "trace_case", "shape": shape, "claim_id": "C-002", "seed": 11,
                             "trial": trial, "label": labels["C-002"]})
    out = Path("reports"); out.mkdir(exist_ok=True)
    (out / "trace_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    judges = {name: calibrate(Path(f"data/eval/judge_{name}_public.csv")) for name in ("tone", "helpful")}
    (out / "judge_calibration.json").write_text(json.dumps(judges, ensure_ascii=False, indent=2), encoding="utf-8")
    files = [*Path("lab8").rglob("*.py"), *Path("lab9").glob("*.py"), *Path("config").glob("*.yaml"),
             Path("data/public_claims.jsonl"), Path("data/public_world_state.json"),
             *Path("tests").glob("test_lab9*.py")]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    manifest = {"python": platform.python_version(),
                "packages": {n: version(n) for n in ("pytest", "numpy", "scipy", "pydantic-evals", "PyYAML")},
                "source_sha256": {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
                "code_commit": commit.stdout.strip() if commit.returncode == 0 else "not available; see source_sha256"}
    (out / "environment.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for e in evidence:
        t = e["trial"]
        print(e.get("fm", e.get("shape")), e["claim_id"], t["lab8_pass"], t["lab8_reason"], t["snapshot"])
        for i, event in enumerate(t["events"], 1):
            print(i, event["kind"], event.get("payload"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
