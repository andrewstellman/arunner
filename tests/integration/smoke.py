"""Basic smoke test (FR-51) — a small curated subset of the integration
scenarios that validates Arunner's CORE functionality fast.

This is the "does the engine still basically work" gate: five ticker-driven
runs covering the autonomous loop to `done`, the STOP read-only invariant,
pool-limited staggered dispatch, crash-resume, and the wrap adapter
(cross-agent shell dispatch). It reuses the real scenario runner + the
INDEPENDENT stdlib checker (the harness never grades its own homework), so a
green smoke run means the same thing a green full-suite run does, just over a
core subset.

Run:  python3 tests/integration/smoke.py
Exit: 0 if every smoke scenario passes; 1 otherwise.

The full scenario catalogue (all 11 + the planned continuation_contract) is
tracked in docs/INTEGRATION_TEST_PLAN.md. Keep this subset small and core;
add new rows there, not here, unless they are genuinely smoke-level.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]

# The curated core subset. Order = rough dependency order (loop first).
SMOKE = [
    "autonomous_loop",        # autonomous multi-tick loop reaches `done`
    "stop_readonly",          # STOP halts and the STOP tick mutates nothing
    "pool_staggered",         # pool limit respected; dispatch staggered
    "resume_continues",       # PAUSE then RESUME: queued entry dispatches after resume -> done
    "wrap_adapter_completes", # wrap adapter (shell dispatch) drives to done
]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    runner = _load("wc_smoke_runner", _HERE / "runner.py")
    checker = _load("wc_smoke_checker", _HERE / "checker.py")
    scenarios_dir = _HERE / "scenarios"

    print("Arunner smoke test — %d core scenarios\n" % len(SMOKE))
    failed = []
    for name in SMOKE:
        sc = scenarios_dir / name
        if not sc.is_dir():
            print("  MISSING  %s (no scenario folder)" % name)
            failed.append(name)
            continue
        with tempfile.TemporaryDirectory() as d:
            run_dir = runner.run_scenario(sc, d)
            expected = json.loads((sc / "scenario.json").read_text())["expected"]
            failures = checker.check(run_dir, expected)
        if failures:
            print("  FAIL     %s" % name)
            for f in failures:
                print("             - %s" % f)
            failed.append(name)
        else:
            print("  PASS     %s" % name)

    print()
    if failed:
        print("SMOKE FAILED — %d/%d scenario(s) failed: %s"
              % (len(failed), len(SMOKE), ", ".join(failed)))
        return 1
    print("SMOKE PASSED — %d/%d core scenarios green" % (len(SMOKE), len(SMOKE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
