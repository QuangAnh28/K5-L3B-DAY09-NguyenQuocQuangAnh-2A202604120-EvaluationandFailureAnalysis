"""Final tests and optional byte-for-byte source lock against supplied Day 8 ZIP."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import yaml
from lab8.console import utf8_stdio


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--day8-zip")
    args = parser.parse_args()
    records_path = Path("reports/verification.json")
    records = json.loads(records_path.read_text(encoding="utf-8"))
    command = [sys.executable, "-m", "pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9"]
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
    Path("reports/tests_lab9.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    records.append({"name": "tests_lab9_final", "command": "python -m pytest -q -m student -o addopts= -k lab9",
                    "expected_exit": 0, "actual_exit": proc.returncode})
    records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(proc.stdout + proc.stderr)
    if proc.returncode: return 1
    workflow = yaml.safe_load(Path("../.github/workflows/eval-gate.yml").read_text(encoding="utf-8"))
    assert {"eval-gate", "eval-gate-v2"} <= workflow["jobs"].keys()
    harness = yaml.safe_load(Path("harness_map.yaml").read_text(encoding="utf-8"))
    assert harness["harness_map_version"] == "1.2" and "eval" in harness["sections"]
    if args.day8_zip:
        hashes, mismatches = {}, []
        with zipfile.ZipFile(args.day8_zip) as z:
            for name in z.namelist():
                if "/src/lab8/" not in name or name.endswith("/"): continue
                relative = name.split("/src/", 1)[1]
                expected = z.read(name)
                actual = Path(relative).read_bytes()
                hashes[relative] = hashlib.sha256(expected).hexdigest()
                if actual != expected: mismatches.append(relative)
        result = {"archive": Path(args.day8_zip).name, "files": len(hashes),
                  "unchanged": not mismatches, "mismatches": mismatches, "sha256": hashes}
        Path("reports/day8_source_lock.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Original Lab 8 source: {len(hashes)} files, {len(mismatches)} byte differences")
        if mismatches: return 1
    print("Final tests, workflow YAML and harness mapping passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
