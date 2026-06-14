# Panelist B — Publish-Safety (FR-33) Review

**Iteration:** 13a (real packaging + publish-safety), UNCOMMITTED working tree
**Repo:** `arunner` @ `/Users/andrewstellman/Documents/wakecycle` (git `main`, HEAD `ae24c92`)
**Reviewer:** B (independent/adversarial). I personally ran every gate below from the working tree.

FR-33 requires: clean-clone cold build, built-artifact end-to-end test in a throwaway
environment, and a dry-run before any live upload — and NOTHING actually published.
All four were exercised. Result: **SHIP**.

---

## 1. CLEAN-CLONE COLD BUILD — PASS

rsync'd the current uncommitted working tree into a pristine temp dir
(`/tmp/arunner_coldbuild.tFgmuP`) excluding `.git repos __pycache__ *.pyc harness_runs
runs dist build *.egg-info node_modules`. The copy contained no `.git`/`__pycache__`,
and `arunner/engine/` carried all six modules.

`python3 -m build` (isolated, no dev deps — build 1.3.0) succeeded:

```
Successfully built arunner-0.1.0.tar.gz and arunner-0.1.0-py3-none-any.whl
```

`python3 -m twine check dist/*` — BOTH artifacts PASSED:

```
Checking dist/arunner-0.1.0-py3-none-any.whl: PASSED
Checking dist/arunner-0.1.0.tar.gz: PASSED
```

**Wheel contents (engine ships):**

```
arunner/__init__.py
arunner/__main__.py
arunner/cli.py
arunner/engine/__init__.py
arunner/engine/demo_worker.py
arunner/engine/heartbeat.py
arunner/engine/incontext.py
arunner/engine/jobs.py
arunner/engine/tick.py
arunner/engine/ticker.py
arunner-0.1.0.dist-info/{licenses/LICENSE,METADATA,WHEEL,entry_points.txt,top_level.txt,RECORD}
```

Required engine modules `{tick,ticker,heartbeat,jobs,incontext,demo_worker}.py` +
`arunner/__init__.py` + `arunner/cli.py` are ALL present. The installed CLI will not be
broken by a missing engine.

**entry_points.txt declares all three console scripts:**

```
[console_scripts]
arunner = arunner.cli:main
arunner-heartbeat = arunner.engine.heartbeat:main
arunner-ticker = arunner.engine.ticker:main
```

## 2. THROWAWAY-ENV END-TO-END — PASS

Fresh venv (`/tmp/arunner_venv.f6cel7`), `pip install`ed the built **WHEEL** (not source).
All smoke ran the INSTALLED `<venv>/bin/*` console scripts.

**2a — version:** `arunner --version` → `arunner 0.1.0`. ✓

**2b — demo to done, zero API spend:** concretized `references/examples/demo_shell.json`
(3 wrap/shell jobs, pool 2) — json-loaded, set the 3 `target_repo` fields to mkdir'd temp
dirs, wrote a temp plan. Set `ARUNNER_RUNS_DIR` to a temp dir. `arunner run <plan>
--no-drive` initialized run-dir `…/runs/20260614T064832Z`. Looped
`arunner-ticker --once <run-dir>` (0.3s between). Reached **`done: true` at tick 3**:

```
Queue: 0  Claimed: 0  Running: 0  Stalled: 0  Completed: 3  Failed: 0
DONE - all runs terminal. No further ticks.
```

harness_status.json: `"done": true`, counts completed=3 / failed=0, all three runs
`state: completed`, `last_hb_status: COMPLETED`, `dispatch_mode: shell`. Pool-2 cadence is
visible (demo-a/demo-b claimed together at 1781419719.154, demo-c later at .581). Shell
wrap adapter = ZERO API spend confirmed.

**2c — status / summary:** `arunner status <run-dir>` rc=0, non-empty table.
`arunner summary <run-dir>` rc=0, first line `# arunner run summary`, per-run rows with
`wrap: 'python3' exited 0`.

**2d — heartbeat:** `arunner-heartbeat emit … --status IN_PROGRESS` rc=0;
`arunner-heartbeat terminal … --status COMPLETED --result-file <rf> --summary done` rc=0.
File ends with exactly **2 valid JSON lines** (IN_PROGRESS then COMPLETED). Negative
control — `terminal` WITHOUT `--result-file` correctly fails **rc=2** (argparse required
arg), which is correct behavior, not a bug.

## 3. DRY-RUN (no upload) — PASS

Python: twine check clean (above), version 0.1.0, name `arunner` (pyproject + METADATA).
npm: `npm publish --dry-run` from repo root PACKED (no upload), tarball `arunner-0.1.0.tgz`,
name `arunner`, version 0.1.0, **total files: 4** — exactly:

```
LICENSE, README.md, npm-bin/arunner.js, package.json
```

`(dry-run)` annotation present on the publish line. `node npm-bin/arunner.js` loads (rc=0).

## 4. NOTHING WAS PUBLISHED — CONFIRMED

I ran NO `twine upload` and NO real `npm publish` — only `npm publish --dry-run`. No
upload occurred to PyPI or npm. The repo working tree is unchanged (HEAD still `ae24c92`,
same uncommitted modifications as at start; no commits, no pushes). Build artifacts were
produced only inside the throwaway temp dir, not the repo root. All temp dirs and the venv
were removed at the end of the review.

---

VERDICT: SHIP
