# Instruction 003 — FIX: shell gates run from the wrong cwd (false-failure)

**Repo:** `~/Documents/arunner`, worktree `~/Documents/arunner-fix-gate-cwd` on branch `fix-gate-cwd`, created off `fr-61-65-impl`:
`git -C ~/Documents/arunner worktree add ~/Documents/arunner-fix-gate-cwd -b fix-gate-cwd fr-61-65-impl`.
Confirm the branch (`git -C ~/Documents/arunner-fix-gate-cwd rev-parse --abbrev-ref HEAD`). Do NOT work on `main` or `fr-61-65-impl` directly. Same line as FR-61–65 (0.2.0).

**One-line goal:** make `_eval_shell_gate` run the gate subprocess with `cwd = the step/entry target_repo`, so a gate's success no longer depends on the orchestrator's incidental cwd.

## The bug (surfaced 2026-06-19, QPB v1.5.10 integration/regression run)
`_eval_shell_gate` (`arunner/engine/tick.py`, the `subprocess.run` at ~line 1769) runs the gate with **no `cwd=`**, so it inherits the orchestrator process's cwd (the arunner repo root). A QPB gate `python3 -m bin.validate_phase_artifacts {TARGET_REPO} --phase 1` needs cwd to contain an importable `bin` package; from the arunner root → `ModuleNotFoundError` → exit 1 → unmapped nonzero → `halt` → three phase-1 runs that ACTUALLY PASSED were marked failed. The phases succeeded; the gate plumbing produced a false negative.

## The fix (one argument + tests)
In `_eval_shell_gate`, pass `cwd=target_repo` to the gate subprocess. The resolved absolute target_repo is already in `values["TARGET_REPO"]` (from `_gate_values` ~line 1698 = `str(step.get("target_repo") or entry.get("target_repo",""))` — step override wins; schema enforces an absolute path and `check_plan` enforces existence):
```python
proc = subprocess.run(
    argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    timeout=_GATE_TIMEOUT_SECONDS,
    cwd=(values.get("TARGET_REPO") or None),
)
```
Semantics: a shell gate runs in the step/entry `target_repo` — where the worker operated and where the artifacts it checks live. Right general default, not QPB-specific.

**Keep the existing `except (OSError, subprocess.SubprocessError): return "internal_error"` unchanged.** It already handles a deleted/nonexistent target_repo (`FileNotFoundError` is an `OSError`) → `internal_error`, the correct fail-closed outcome (Council-confirmed). The `or None` preserves current behavior when target_repo is empty.

**Do NOT change:** the exit-code→outcome mapping, the `outcomes`/`default` handling, the reasoning-gate path, gate.json persistence/read-on-resume, or the FR-18 exit-code-only firewall. This is a one-argument addition + tests.

**Out of scope — flag, do NOT fix here:** `_run_auth_check` (`tick.py` ~line 2603) has the SAME no-cwd pattern — its auth_check subprocess also runs from the orchestrator's incidental cwd. Record it in your output as a known sibling for a separate instruction; do not touch it in this fix.

## Tests — `tests/test_gates.py`, new class `ShellGateCwdTests(_Base)`, mutation-verified
Use the **sentinel-file** form (NOT `os.getcwd()==EXPECT` — `/tmp`→`/private/tmp` symlinks on macOS make a path-equality check flaky):
- `target_repo = str(self.tmp)` (the existing `_Base` tempdir); write a sentinel into it: `(self.tmp / "sentinel.txt").write_text("x")`.
- Gate argv (relative path — resolves against cwd): `[_PY, "-c", "import os,sys; sys.exit(0 if os.path.exists('sentinel.txt') else 1)"]`.
- Assert the gate outcome is `"continue"` with the fix applied.
- **Mutation proof:** remove `cwd=` from the `subprocess.run`; the gate then runs from the engine's incidental cwd, `sentinel.txt` is absent → exit 1 → `"halt"`. Confirm the test FAILS under that mutation (the pin bites), then restore.
- Add the repo's standard `MUTATION-VERIFY EVIDENCE` header block to the test, matching the format already at the top of `tests/test_gates.py`, documenting this mutation + observed outcome.

**No new tests are required for** the `cwd=None` fallback (target_repo is schema-required + non-empty for any `--check`-clean plan; the `or None` is defensive-only) or the nonexistent-target_repo path (already covered fail-closed by the existing `OSError` catch → `internal_error`). State this in your output so the omission is justified, not accidental.

Confirm the existing `test_gates.py` cases still pass unchanged. Run the full suite with the repo's standard runner (per the CI workflow: `python3 -m unittest discover tests`) **≥3×**; report pass counts + Python version.

## §9 / REQUIREMENTS
In `docs/REQUIREMENTS.md`, the FR-63 gate row (~line 481): add that the shell gate argv runs with `cwd=target_repo` (mutation-verified by the new sentinel test), and update the row's test count to include the new test(s).

## Council — mandatory 3-panel self-Council
`reviews/003_self_council/`, committed. Charters: **A** correctness (cwd=target_repo fixes it; nonexistent→internal_error preserved); **B** regression-safety (existing gate tests unchanged; FR-18 / measurement / persistence untouched; stdlib-only); **C** test-sufficiency (the sentinel pin bites; mutation evidence present). Iterate to unanimous SHIP.

## Commit / scope / output
Checkpoint commit on `fix-gate-cwd`, **local only — do NOT push or merge.** Output → `outputs/003-fix-gate-cwd.md`: the diff, the new test + mutation proof, suite counts ×3 + Python version, the `_run_auth_check` follow-up note, the 3-panel synthesis, and `git -C ~/Documents/arunner-fix-gate-cwd log --oneline -5`.
