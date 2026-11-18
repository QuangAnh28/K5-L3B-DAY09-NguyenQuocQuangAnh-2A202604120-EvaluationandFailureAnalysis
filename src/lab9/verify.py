"""Run public acceptance checks; reports/logs are produced by commands, never edited."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from lab8.console import utf8_stdio


def main():
    utf8_stdio()
    out = Path("reports"); out.mkdir(exist_ok=True)
    records = []
    def run(name, args, expected=0):
        command = [sys.executable, "-m", *args]
        print(f"Running {name}...", flush=True)
        p = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONUTF8": "1"})
        (out / f"{name}.txt").write_text(p.stdout + p.stderr, encoding="utf-8")
        records.append({"name": name, "command": "python -m " + " ".join(args),
                        "expected_exit": expected, "actual_exit": p.returncode})
        (out / "verification.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        print(f"{name}: exit {p.returncode} (expected {expected})", flush=True)
        if p.returncode != expected:
            print(p.stdout + p.stderr)
            raise SystemExit(1)
        return p.stdout
    run("smoke", ["lab9.smoke"])
    run("tests_lab9", ["pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9"])
    run("tests_evalset", ["pytest", "-q", "-o", "addopts=", "tests/test_lab9_evalset.py"])
    run("tests_host", ["pytest", "-q"])
    run("evalset_v1", ["lab9.evalset", "--check"])
    run("evalset_v2", ["lab9.evalset", "--v2"])
    run("judge_tone", ["lab9.judge", "--csv", "data/eval/judge_tone_public.csv", "--audit", "10"])
    run("judge_helpful", ["lab9.judge", "--csv", "data/eval/judge_helpful_public.csv", "--audit", "25"], 1)
    for version in ("v1", "v2"):
        spec = "config/metric_spec.yaml" if version == "v1" else "config/metric_spec_v2.yaml"
        baseline = f"reports/baseline_{version}.json"
        run(f"baseline_{version}", ["lab9.eval", "--shape", "swarm", "--spec", spec, "--out", baseline])
        run(f"gate_self_{version}", ["lab9.gate", "--pr", baseline, "--baseline", baseline, "--spec", spec,
                                    "--base-spec", spec])
        shapes = ("fixed", "seeded_regression") if version == "v1" else (
            "fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression")
        for shape in shapes:
            path = f"reports/eval_{shape}.json" if version == "v1" else f"reports/eval_{shape}_v2.json"
            run(f"eval_{shape}_{version}", ["lab9.eval", "--shape", shape, "--spec", spec, "--out", path])
            text = run(f"gate_{shape}_{version}", ["lab9.gate", "--pr", path, "--baseline", baseline,
                       "--spec", spec, "--base-spec", spec], 0 if shape in ("fixed", "honest_refactor") else 1)
            if shape == "seeded_regression" and "pass_rate" not in text.split("blocked:")[-1]:
                raise RuntimeError("seeded_regression must be blocked on pass_rate")
        if version == "v1":
            run("ci_check", ["lab9.ci_check", "--pr", baseline, "--baseline", baseline, "--spec", spec])
            run("detect", ["lab9.mutation", "--detect"])
        else:
            run("aa", ["lab9.mutation", "--spec", spec, "--aa", "66,77,88,99,110"])
            run("mutation", ["lab9.mutation", "--spec", spec, "--baseline", baseline, "--base-spec", spec])
            run("traps", ["lab9.traps", "--pr", "reports/eval_slice_regression_v2.json", "--baseline", baseline, "--spec", spec])
            for name in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
                trap_spec = f"reports/traps/{name}.spec.yaml" if name == "loosened_spec" else spec
                run(f"trap_{name}", ["lab9.gate", "--pr", f"reports/traps/{name}.json", "--baseline", baseline,
                                     "--spec", trap_spec, "--base-spec", spec], 1)
    run("tests_lab9", ["pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9"])
    run("evidence", ["lab9.evidence"])
    print(f"All {len(records)} acceptance commands returned expected exits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
