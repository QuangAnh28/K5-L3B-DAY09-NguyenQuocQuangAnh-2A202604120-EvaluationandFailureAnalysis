"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats, evalset
from lab9.graders import GRADERS
from lab9.eval import SPEC, load_spec, per_item


def _spec_problems(spec: dict, title: str) -> list[str]:
    """Reject nonnumeric/nonfinite bounds before any ordered comparison."""
    problems = []
    for section in ("metrics", "slices"):
        entries = spec.get(section, [])
        if not isinstance(entries, list):
            problems.append(f"{title}: {section} must be a list")
            continue
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append(f"{title}: invalid {section} entry")
                continue
            ident = entry.get("id") if section == "metrics" else (entry.get("name"), entry.get("metric"))
            if ident in seen:
                problems.append(f"{title}: duplicate {section} {ident}")
            seen.add(ident)
            bounds = entry.get("threshold", {}) if section == "metrics" else entry
            if not isinstance(bounds, dict):
                problems.append(f"{title}: invalid threshold {ident}")
                continue
            for key in ("min", "max", "max_increase"):
                if key in bounds and (type(bounds[key]) not in (int, float) or not math.isfinite(bounds[key])):
                    problems.append(f"{title}: nonfinite/nonnumeric bound {ident}/{key}")
            if "blocking" in entry and type(entry["blocking"]) is not bool:
                problems.append(f"{title}: blocking must be boolean: {ident}")
            if "no_significant_drop" in bounds and type(bounds["no_significant_drop"]) is not bool:
                problems.append(f"{title}: no_significant_drop must be boolean: {ident}")
    return problems


def _same_eval_set(spec: dict, base_spec: dict, report: dict) -> bool:
    """Version text alone cannot unlock ratchet for unchanged dataset bytes.

    A genuine migration is allowed when the old spec identifies different data,
    the new dataset's own item versions match the new spec, and its baseline
    has been regenerated. Minimal in-memory reports without a dataset reference
    cannot prove a migration and therefore keep the ratchet.
    """
    if spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        return True
    old_path, new_path = base_spec.get("eval_set"), spec.get("eval_set")
    if not old_path or old_path == new_path:
        return True
    if Path(old_path).is_file():
        return evalset.sha12(Path(old_path)) == report.get("manifest", {}).get("eval_set_sha")
    return True  # no evidence that this is a different dataset


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = _spec_problems(spec, "spec")
    if base_spec is not None:
        problems += _spec_problems(base_spec, "base_spec")
    if problems:
        return problems
    # Bind the declared version and SHA to the actual immutable evaluation items.
    if spec.get("eval_set"):
        path = Path(spec["eval_set"])
        try:
            items = evalset.load_jsonl(path)
            versions = {it.get("eval_set_version") for it in items}
            if not items or versions != {spec.get("eval_set_version")}:
                problems.append("spec eval_set_version differs from dataset item versions")
            sha = evalset.sha12(path)
            for title, report in (("PR", pr), ("baseline", base)):
                if report.get("manifest", {}).get("eval_set_sha") != sha:
                    problems.append(f"{title}: SHA differs from spec dataset bytes")
                if report.get("manifest", {}).get("items") != len(items):
                    problems.append(f"{title}: item count differs from dataset")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            problems.append(f"cannot validate spec dataset: {type(exc).__name__}")
    graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
    for title, report in (("PR", pr), ("baseline", base)):
        rows = report.get("rows", [])
        manifest = report.get("manifest", {})
        seeds = manifest.get("seeds", [])
        if "eval_set_version" in manifest and manifest["eval_set_version"] != spec.get("eval_set_version"):
            problems.append(f"{title}: manifest eval-set version differs from spec")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if not seeds or len(set(seeds)) != len(seeds):
            problems.append(f"{title}: empty or duplicate manifest seeds")
        if not rows:
            problems.append(f"{title}: empty report")
        if len(rows) != manifest.get("items", 0) * len(seeds):
            problems.append(f"{title}: row count differs from manifest")
        counts = Counter(pairs)
        if any(n != 1 for n in counts.values()):
            problems.append(f"{title}: duplicate item/seed pair")
        items = {r.get("item_id") for r in rows}
        if len(items) != manifest.get("items") or set(pairs) != {(i, seed) for i in items for seed in seeds}:
            problems.append(f"{title}: incomplete item x seed grid")
        if "seeds" in spec and set(seeds) != set(spec["seeds"]):
            problems.append(f"{title}: seeds differ from spec")
        if report.get("evaluator_failures"):
            problems.append(f"{title}: evaluator_failures is nonempty")
        for mid, val in report.get("metrics", {}).items():
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                problems.append(f"{title}: nonfinite/missing metric {mid}")
        for m in spec["metrics"]:
            if m["id"] not in report.get("metrics", {}):
                problems.append(f"{title}: missing metric {m['id']}")
        for mid in graded:
            values = [r.get(mid) for r in rows]
            if any(type(v) is not bool for v in values):
                problems.append(f"{title}: invalid/missing row value {mid}")
            elif values:
                expected = sum(values) if mid in ("secret_leak", "approval_bypass") else round(sum(values) / len(values), 4)
                val = report.get("metrics", {}).get(mid)
                if not isinstance(val, (int, float)) or not math.isclose(val, expected, abs_tol=0.000051):
                    problems.append(f"{title}: aggregate disagrees with rows: {mid}")
        # Derived reliability/cost metrics must also agree with complete raw rows.
        if rows and all(type(r.get("pass_rate")) is bool for r in rows):
            by_item = [[r["pass_rate"] for r in rows if r["item_id"] == i] for i in items]
            derived = {"pass_5": sum(all(v) for v in by_item) / len(by_item)}
            for mid in report.get("metrics", {}):
                for prefix, fn in (("pass_at_", stats.pass_at_k), ("pass_hat_", stats.pass_hat_k)):
                    if mid.startswith(prefix):
                        try:
                            k = int(mid[len(prefix):])
                            derived[mid] = sum(fn(len(v), sum(v), k) for v in by_item) / len(by_item)
                        except ValueError:
                            problems.append(f"{title}: invalid reliability metric {mid}")
            successes = sum(r["pass_rate"] for r in rows)
            if "cost_per_success" in report.get("metrics", {}):
                costs = [r.get("cost") for r in rows]
                if not successes or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in costs):
                    problems.append(f"{title}: invalid cost or no successes")
                else:
                    derived["cost_per_success"] = sum(costs) / successes
            for mid, expected in derived.items():
                if mid not in report.get("metrics", {}):
                    continue
                val = report["metrics"][mid]
                if not isinstance(val, (int, float)) or not math.isclose(val, round(expected, 4), abs_tol=0.000051):
                    problems.append(f"{title}: aggregate disagrees with rows: {mid}")
    pr_pairs = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_pairs = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_pairs != base_pairs:
        problems.append("PR item/seed set differs from baseline")
    base_tags = {(r.get("item_id"), r.get("seed")): set(r.get("slices") or []) for r in base.get("rows", [])}
    for r in pr.get("rows", []):
        if set(r.get("slices") or []) != base_tags.get((r.get("item_id"), r.get("seed")), set()):
            problems.append(f"slice tags changed: {r.get('item_id')}")
    for title, report in (("PR", pr), ("baseline", base)):
        tags = {}
        for r in report.get("rows", []):
            tag = set(r.get("slices") or [])
            if r["item_id"] in tags and tags[r["item_id"]] != tag:
                problems.append(f"{title}: inconsistent slice tags across seeds")
            tags[r["item_id"]] = tag
    if base_spec is not None and _same_eval_set(spec, base_spec, pr):
        for section in ("metrics", "slices"):
            key = (lambda m: m["id"]) if section == "metrics" else (lambda m: (m["name"], m["metric"]))
            current = {key(m): m for m in spec.get(section, [])}
            for old in base_spec.get(section, []):
                ident = key(old)
                new = current.get(ident)
                if new is None:
                    problems.append(f"ratchet: removed {section} {ident}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: removed blocking {ident}")
                ot = old.get("threshold", {}) if section == "metrics" else old
                nt = new.get("threshold", {}) if section == "metrics" else new
                for bound in ("min", "max", "max_increase"):
                    if bound in ot and (bound not in nt or (nt[bound] < ot[bound] if bound == "min" else nt[bound] > ot[bound])):
                        problems.append(f"ratchet: loosened {ident}/{bound}")
                if ot.get("no_significant_drop") and not nt.get("no_significant_drop"):
                    problems.append(f"ratchet: removed no_significant_drop {ident}")
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        ident = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        fail = not a or set(a) != set(b)
        value = sum(a.values()) / len(a) if a else None
        note = ""
        if value is not None:
            fail |= "min" in entry and value < entry["min"]
            if entry.get("no_significant_drop") and a.keys() == b.keys():
                keys = sorted(a)
                delta, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                fail |= hi < 0
        if fail and entry.get("blocking"):
            blocked.append(ident)
        verdict = "BLOCK" if fail and entry.get("blocking") else "warn" if fail else "ok"
        lines.append(f"  {ident} {value} {note} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
