# Panelist B — Grading Soundness (instr 042)

Reviewer B, independent/adversarial. Charter: the new acceptance checks are REAL,
gradeable from DURABLE artifacts, and PINNED. Repo `arunner` @ `/Users/andrewstellman/Documents/wakecycle`,
Python 3.14.5. Work UNCOMMITTED (`checker.py`, `test_acceptance_checker.py` modified;
uc2–uc5 plan/expected JSON untracked).

## 1. `no_double_dispatch` is sound + PIN bites — PASS

Checker section 9 (`checker.py` ~L324-348) iterates `status["runs"]` keys, opens
`<run-dir>/<run>/heartbeat.ndjson`, counts lines with `status == "STARTING"`, and
appends a `double-dispatch` failure when `starts > 1`. This is the durable FR-6
idempotency signal: an entry past `queued` is never re-dispatched, so a second
worker (= second STARTING line) is the only way the count exceeds 1. The run keys
(`run-01`, `run-02`) align with the heartbeat sub-dir names.

Unit tests `NoDoubleDispatch`: `test_single_start_per_run_passes` ([1,1] → []),
`test_double_start_fails` ([1,2] → flags `run-02`, marked `# PIN`).

MUTATION BITE (shutil.copy2 snapshot → break → purge __pycache__ → run → restore → re-purge):
changed `if starts > 1:` to `if False and starts > 1:`.
Result: `test_double_start_fails` FAILED (`AssertionError: [] ... `), `test_single_start_per_run_passes`
still passed — confirming the FAIL test is the load-bearing PIN. Restored via
shutil.copy2; re-verified `NoDoubleDispatch` → 2 passed. Post-restore `checker.py`
is byte-identical to the pristine snapshot (`diff -q` clean).

## 2. UC-3 snapshot-compare is real — PASS

`stop_readonly` section (~L263-282) loads the pre-STOP snapshot (`meta.pre_stop_status`,
else `expected["before_snapshot"]`, else `<run-dir>/_before_snapshot.json`) and
compares `cycle` + every `runs[*].state`. `StopReadonlySnapshot` (3 tests):
byte-identical snapshot passes; a snapshot with `cycle=99` FAILS with a `cycle`
message; a missing snapshot is flagged. All 3 pass. A differing snapshot is
detected — real, not a no-op.

## 3. CLI grades from durable artifacts — PASS

Hand-built a 2-run durable run-dir (harness_status.json + per-run heartbeat.ndjson +
results/), expected carrying `no_double_dispatch: true`.
- Clean run (1 STARTING each): `CHECK PASSED`, **EXIT=0**.
- Injected a 2nd STARTING into `run-02`'s heartbeat: `CHECK FAILED (1): double-dispatch:
  run-02 was STARTED 2 times`, **EXIT=1**.

## 4. UC-5 floor plan grades via CLI on a ticker-produced run-dir — PASS

Substituted `{STUB}` → abs path of `tests/integration/stub_worker.py` into a temp
plan; temp `ARUNNER_RUNS_DIR`. `ticker.py --once <plan>` bootstrapped the run-dir
(3 entries, pool_size 2); repeated `ticker.py --once <run-dir>` (sleep 0.3) until
`done=True` (counts.completed=3). Real workers wrote STARTING x1 to each of
run-01/02/03's heartbeat. `checker.py <run-dir> uc5_expected.json` → `CHECK PASSED`,
**EXIT=0** (expected includes `no_double_dispatch: true`). Temp dirs cleaned.

## 5. Full suite — PASS

`python3 -m pytest -q | tail -1` → **269 passed in 25.31s**. Working tree restored
to exactly the two intended modified files.

## Verdict

The `no_double_dispatch` check counts a durable, real-run-produced signal, bites
under mutation, and is pinned by the FAIL test. The UC-3 snapshot-compare detects
a changed snapshot. The CLI grades correctly from durable artifacts (exit 0 clean,
exit 1 on injected double-dispatch) and on a live ticker-produced UC-5 run-dir.

VERDICT: SHIP
