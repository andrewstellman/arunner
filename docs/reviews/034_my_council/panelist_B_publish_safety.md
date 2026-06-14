# Panelist B — Publish-Safety Evidence (iteration 13a, FR-33)

**Charter:** Verify the FR-33 publish-safety gates ACTUALLY ran and passed. Do not trust the worker's "SHIP."

**Repo:** `/Users/andrewstellman/Documents/wakecycle` — HEAD `6dc8016` (matches the worker's claim).
**Worker output reviewed:** `/Users/andrewstellman/Documents/QPB/runner/1.5.9/outputs/034-13a-packaging-and-publish-safety.md`

## Verdict: **SHIP**

All four FR-33 gates were independently reproduced from a clean copy. The worker's evidence is accurate and, in two cases, I drove a *stronger* reproduction than the worker reported (full demo-to-`done` lifecycle through the installed console scripts from outside the source tree). No gate was claimed-but-unreproducible.

One non-blocking note (not a 13a defect): the bundled demo plan and the default runs-root are package-relative, documented below — does not affect ship-readiness.

---

## Gate-by-gate

### Gate 1 — Clean-build + twine check — RAN ✅ PASSED ✅
Built sdist+wheel from a pristine copy (`cp -r` of the repo into `/tmp/arsrc2`, fresh `build`+`twine` venv, `rm -rf dist build *.egg-info`, isolated `python -m build`):

```
Successfully built arunner-0.1.0.tar.gz and arunner-0.1.0-py3-none-any.whl
Checking dist/arunner-0.1.0-py3-none-any.whl: PASSED
Checking dist/arunner-0.1.0.tar.gz: PASSED
```

- Name `arunner`, version `0.1.0` — confirmed in both artifact filenames and wheel METADATA.
- **Engine ships in the wheel** (the core fix this iteration existed to make). Wheel contents:
  `arunner/{__init__,__main__,cli}.py` + `arunner/engine/{__init__,demo_worker,heartbeat,incontext,jobs,tick,ticker}.py`.
- `entry_points.txt` carries all three console scripts:
  `arunner = arunner.cli:main`, `arunner-heartbeat = arunner.engine.heartbeat:main`, `arunner-ticker = arunner.engine.ticker:main`.
- **Stale-parenthetical fix verified:** METADATA `Summary:` is clean — no `"(0.0.1 reserves the name; the harness ships here shortly.)"`. (The `0.0.1` strings that remain are in the README naming-history body, which is honest provenance, not the PyPI description.)

Matches the worker's claimed Gate-1 evidence exactly.

### Gate 2 — Throwaway-venv install + demo-to-`done` smoke — RAN ✅ PASSED ✅
Installed the built **wheel** into a fresh venv (`/tmp/iv`), then drove a real run using only the **installed** console scripts, from cwd `/tmp` (outside the source tree). Import resolved to `…/site-packages/arunner/__init__.py` — proving the installed package, not the source tree.

- `arunner --version` → `arunner 0.1.0` (rc 0). All three scripts installed (`arunner`, `arunner-ticker`, `arunner-heartbeat`).
- Concretized the bundled demo (`references/examples/demo_shell.json`, 3 SHELL jobs, pool 2, placeholder repos → `/tmp/smoke/...`), `arunner run plan.json` (rc 0) initialized the run-dir, then drove `arunner-ticker --once` until terminal:
  ```
  tick 5 -> done=True
  ```
- `arunner status` (rc 0):
  ```
  Queue: 0  Claimed: 0  Running: 0  Stalled: 0  Completed: 3  Failed: 0
  DONE - all runs terminal. No further ticks.
  ```
- `arunner summary` (rc 0): first line `# arunner run summary`; `**Totals** - completed: 3, failed: 0, abandoned: 0, auth/launch-failed: 0 (of 3 job(s))`.
- **Zero API spend** — SHELL jobs run `python3 -c "print(...)"` via the FR-40 wrap adapter; doneness = child exit 0. No live agent involved.

This is a stronger reproduction than the worker's report (I ran the full lifecycle through the installed scripts end-to-end). Confirms the worker's Gate-2 claim.

### Gate 3 — npm dry-run — RAN ✅ PASSED ✅
npm 10.9.8 available. `npm publish --dry-run` (rc 0):
```
📦  arunner@0.1.0
  LICENSE  README.md  npm-bin/arunner.js  package.json   (total files: 4)
Publishing to https://registry.npmjs.org/ with tag latest and default access (dry-run)
```
- Name `arunner`, version `0.1.0`, exactly the 4 files declared in `package.json` `"files": ["npm-bin/","README.md","LICENSE"]` (+ package.json itself). Matches worker evidence.
- **npm launcher honesty verified live.** `npm-bin/arunner.js` is a genuine thin delegator:
  - From a neutral cwd with the installed package on PATH → execs `python -m arunner` → `arunner 0.1.0` (rc 0). Really delegates; does not reimplement the CLI in Node.
  - From a neutral cwd with a clean Python (no `arunner`) → prints the pipx hint (`pipx install arunner` / `python3 -m pip install arunner`) and exits non-zero (rc 127). No false "Node CLI" claim.
  - (Probing `import arunner` from the repo root succeeds off the source dir on `sys.path` — a cwd artifact, not a launcher bug; the delegation/hint logic is correct.)

### Gate 4 — Nothing published — VERIFIED ✅
- No `twine upload` and no non-dry `npm publish` anywhere in the 13a diff (`ae24c92..6dc8016`) or the working tree — only dry-run references exist.
- The three 13a commits (`b5264e9`, `0b7767b`, `6dc8016`) are **local-only**: `git log origin/main..6dc8016` lists all three, i.e. they are not on `origin/main`. Never pushed.
- Publish remains the operator's gated action. Confirms the worker's "nothing published."

---

## Non-blocking observations (do not gate the ship)
1. **Default runs-root is package-relative.** `arunner run` wrote to `…/site-packages/harness_runs/<ts>` and an `ARUNNER_RUNS_ROOT` env var was not honored by the installed CLI. Cosmetically odd for an installed tool (runs land under site-packages), but the run completed correctly and `status`/`summary` resolved fine against it. Worth a follow-up to default runs to CWD/XDG, not a 13a publish-safety failure.
2. **Bundled demo isn't shipped in the wheel.** `references/examples/demo_shell.json` is outside the package (no MANIFEST.in; packages = `arunner`/`arunner.engine` only), and its `target_repo` paths are placeholders requiring concretization. The worker's report is honest about running the demo from the source tree; the *installed package itself* works (verified Gate 2), the *demo file* just isn't carried inside it. Acceptable for 13a; flag if "installed users can run the bundled demo" ever becomes a requirement.

## Cleanup
All `/tmp` venvs/dirs I created (`/tmp/bv`, `/tmp/iv`, `/tmp/arsrc2`, `/tmp/smoke`, `/tmp/clean_py`, `/tmp/cleanbin`) and the transient `arunner-0.1.0.tgz` from `npm pack` were removed. Repo working tree left as found (pre-existing untracked council scaffolding untouched).
