# Output for 003-fix-gate-cwd.md

**Status:** completed

Fixed the shell-gate cwd false-failure in worktree `~/Documents/arunner-fix-gate-cwd`, branch `fix-gate-cwd` (off `fr-61-65-impl`). **Local only — not pushed, not merged.**

## The diff
`arunner/engine/tick.py` — `_eval_shell_gate`: the gate subprocess now runs with `cwd = target_repo`:
```python
proc = subprocess.run(argv, stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, timeout=_GATE_TIMEOUT_SECONDS,
                      cwd=(values.get("TARGET_REPO") or None))
```
(plus a docstring note explaining the semantic + the 2026-06-19 QPB origin). `values["TARGET_REPO"]` = `_gate_values` = `str(step.get("target_repo") or entry.get("target_repo",""))` (step override wins; schema enforces absolute, `check_plan` enforces existence). The `except (OSError, subprocess.SubprocessError): return "internal_error"` is **unchanged** — it still catches a nonexistent/deleted target_repo (`FileNotFoundError` is an `OSError`) → fail-closed. `or None` preserves prior behavior when target_repo is empty.

**Untouched (as required):** exit-code→outcome mapping, `outcomes`/`default` handling, the reasoning-gate path, gate.json persistence/read-on-resume, the FR-18 exit-code-only firewall (stdout/stderr still DEVNULL; only `returncode` read), the FR-51/measurement fences. stdlib-only (no new imports).

Exactly 3 files changed: `arunner/engine/tick.py`, `tests/test_gates.py`, `docs/REQUIREMENTS.md` (+ the Council artifacts).

## The new test + mutation proof
`tests/test_gates.py` — new class `ShellGateCwdTests(_Base)` with `test_shell_gate_runs_in_target_repo_cwd`:
- `target_repo = str(self.tmp)`; writes `sentinel.txt` into it.
- Gate argv (relative path): `[_PY, "-c", "import os,sys; sys.exit(0 if os.path.exists('sentinel.txt') else 1)"]`.
- With the fix: cwd=target_repo → sentinel found → exit 0 → outcome `continue` → step-02 dispatches. **Passes.**
- **Mutation proof (run this session):** removing the `cwd=` argument → the gate runs from the engine's incidental cwd → `sentinel.txt` absent → exit 1 → unmapped nonzero → `halt` → the test FAILS (`AssertionError: 'halt' != 'continue'`). Restored → passes. The pin bites.
- Sentinel form (not `os.getcwd()==EXPECT`) deliberately avoids the macOS `/tmp`→`/private/tmp` symlink path-equality flakiness. Standard `MUTATION-VERIFY EVIDENCE` header block added to the file, matching the existing format.

**Justified test omissions** (stated so they're deliberate, not accidental):
- *`cwd=None` fallback* — `target_repo` is schema-required + non-empty for any `--check`-clean plan; `("" or None) → None` is the inherit-cwd idiom itself. A test would only re-assert Python truthiness. Defensive-only.
- *nonexistent target_repo* — `subprocess.run(cwd=<bad>)` raises `OSError`, already caught by the existing `except` → `internal_error` (fail-closed); pre-existing behavior, not introduced here.

## Tests
Full suite via the repo's standard runner `python3 -m unittest discover tests`, run **3×**: **Ran 379 tests — OK** each time (378 from instr 002 + 1 new cwd test). Python **3.14.5**. Existing `test_gates.py` cases pass unchanged (15 total in that file now). Deterministic, no flakiness.

## §9 / REQUIREMENTS
`docs/REQUIREMENTS.md` FR-63 §9 row updated: the shell gate argv runs with **`cwd=target_repo`** (mutation-verified by the new sentinel test); test count 13→**14**, PINs 2→**3**; attribution `instr 002 + 003`.

## `_run_auth_check` follow-up note (out of scope — flagged for a separate instruction)
`_run_auth_check` (`arunner/engine/tick.py`) has the **same no-`cwd=` pattern**: its `auth_check` subprocess also runs from the orchestrator's incidental cwd. Not touched in this fix (the instruction scoped it out). Recommend a follow-up instruction to apply the same `cwd=target_repo` treatment (an `auth_check` is per-entry, so the entry's `target_repo` is the natural cwd) with its own test.

## Council (mandatory 3-panel self-Council)
**Unanimous SHIP** (round 1). Artifacts: `reviews/003_self_council/` (panelists A/B/C + `synthesis.md`).
- **A — correctness:** cwd=target_repo resolves the false-failure (step override wins); a bad cwd → `OSError` → `internal_error` fail-closed (repro-confirmed); `or None` preserves prior behavior; sound general default.
- **B — regression-safety:** diff = 3 files only; FR-18 firewall + outcome mapping + reasoning path + gate.json persistence + fences byte-for-byte unchanged; stdlib-only; suite `Ran 379, OK`.
- **C — test-sufficiency:** the sentinel pin bites under mutation (continue→halt); sentinel (not path-equality) form; evidence header present; omissions justified.

## `git -C ~/Documents/arunner-fix-gate-cwd log --oneline -5`
```
116a4d4 FIX: shell gates run with cwd=target_repo (false-failure) (instr 003)
e6aa7d3 FR-61..65 3-panel council: unanimous SHIP + test-evidence fix (instr 002)
d1982b3 docs: flip FR-61..65 §9 rows to VERIFIED (instr 002)
43f8bb9 FR-65: per-run and per-sub-run token reporting (input + output) (instr 002)
3748e59 FR-63 + FR-64: continuation gates + outcome vocabulary (instr 002)
```

## Next action expected from orchestrator
Review + land the `fix-gate-cwd` branch (built off `fr-61-65-impl`; operator merges). Consider filing the `_run_auth_check` cwd follow-up instruction. The QPB-native plan + recall benchmark (the FR-61–65 downstream consumer) can now run with gates that resolve from the correct cwd.
