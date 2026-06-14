# Panelist A — Console script & version single-source (FR-34)

Iteration 13a "real packaging + publish-safety". Reviewing the UNCOMMITTED working
tree at `/Users/andrewstellman/Documents/wakecycle` (branch `main`) against HEAD.
Independent adversarial review; all evidence below is from commands I ran on disk.

---

## 1. `[project.scripts]` maps the real CLI router, not the `_reserve` stub — PASS

`git diff HEAD -- pyproject.toml`:

```
 [project.scripts]
-arunner = "arunner._reserve:main"
+arunner = "arunner.cli:main"
+arunner-ticker = "arunner.engine.ticker:main"
+arunner-heartbeat = "arunner.engine.heartbeat:main"

 [tool.setuptools]
-packages = ["arunner"]
+packages = ["arunner", "arunner.engine"]
```

`arunner = "arunner.cli:main"` (the FR-53 lifecycle router), plus
`arunner-ticker = "arunner.engine.ticker:main"` and
`arunner-heartbeat = "arunner.engine.heartbeat:main"`. The `arunner.engine`
package is added to `[tool.setuptools] packages` so the wheel ships it. All three
required entry points present and correct.

## 2. `_reserve` stub fully retired — PASS

- `ls -la arunner/_reserve.py` → `No such file or directory` (gone from working tree).
- `git show HEAD:arunner/_reserve.py >/dev/null 2>&1` → exit 0 ("HEAD has _reserve.py: YES"): it existed at HEAD and is removed by this change (`git status`: `D arunner/_reserve.py`).
- `git grep -n _reserve -- ':!reviews' ':!docs'` returns ONLY 5 hits, all in
  `tests/test_version_single_source.py`, and every one is a NEGATIVE guard
  (docstring "stub is RETIRED", `assertNotIn("_reserve", pyproject)`,
  `assertFalse((_ROOT/"arunner"/"_reserve.py").exists())`, test-method name).
- `git grep -n "_reserve:main\|arunner\._reserve" -- ':!reviews' ':!docs' ':!tests'`
  → exit 1 (no matches). No dangling entry-point or import reference anywhere in
  package code or config.

## 3. Version single source = `arunner/__init__.py:__version__` (0.1.0); every surface mirrors/reads it — PASS

```
arunner/__init__.py:9:        __version__ = "0.1.0"          <- canonical source
pyproject.toml:7:           version = "0.1.0"
package.json:3:             "version": "0.1.0",
SKILL.md:4:                 version: 0.1.0
plugin.json:4:              "version": "0.1.0",
tick.py:1230 _arunner_version()  reads the package __init__ by path (no literal)
cli.py:31 `from arunner import __version__`; :197 argparse action="version"
```

No surface hardcodes a divergent literal; plugin.json was bumped 0.0.1→0.1.0 to
match (visible in its diff). All five mirrors + two readers agree at 0.1.0.

## 4. Console script & engine banner print the single source — PASS

```
$ python3 -m arunner --version
arunner 0.1.0

$ python3 -c "...exec_module(tick.py); print(m._arunner_version())"
0.1.0
```

## 5. FR-34 drift test rewritten (drops `_reserve`, covers real surfaces) and BITES — PASS

`tests/test_version_single_source.py` is value-agnostic (never hardcodes a version
number; every surface is asserted `== __version__`) and now covers: pyproject,
package.json, SKILL frontmatter, plugin.json, the real console script
(`arunner.cli:main` via `--version`), the engine banner (`tick._arunner_version()`),
and a guard that `arunner.cli:main` is the entry point with `_reserve` absent.

Mutation-bite, console-script test (snapshot/restore via `shutil.copy2`, NEVER git checkout):
- `shutil.copy2('pyproject.toml','/tmp/pyproject_034_snapshot.toml')` (orig sha `86d36d8075de28c7`).
- Mutated scripts line back to `arunner._reserve:main`.
- `pytest tests/test_version_single_source.py -q` →
  `FAILED ...::test_console_script_is_the_real_cli_not_reserve` — `1 failed, 7 passed`.
  Assertion: `'arunner = "arunner.cli:main"' not found`. The test bites.
- Restored via `shutil.copy2(snapshot -> pyproject.toml)`; restored sha
  `86d36d8075de28c7` (matches); `git diff HEAD` shows only the intended 13a change,
  no mutation residue.

Mutation-bite, plugin.json drift (also verified, with pycache purged first):
- Snapshotted, changed `"version": "0.1.0"` → `"0.9.9"`.
- `pytest ...::test_plugin_json_mirrors_canonical` → FAILED. The test bites.
- Restored via `shutil.copy2`; `git diff HEAD` shows only the intended 0.0.1→0.1.0.
- Final clean run: `pytest tests/test_version_single_source.py -q` → `8 passed`.

## 6. Engine moved into the package; old `bin/` gone; nesting path-fixes correct — PASS

- `ls arunner/engine/` → `__init__.py demo_worker.py heartbeat.py incontext.py
  jobs.py tick.py ticker.py` (all six modules + package `__init__.py`).
- `ls bin/` → `No such file or directory` (old engine dir removed; git records
  the six files as renames `bin/* -> arunner/engine/*`).
- `parent.parent` fixes for the deeper `arunner/engine/` nesting
  (`git diff HEAD -M -- bin/tick.py arunner/engine/tick.py`):
  - `runs_root = ... parent.parent / "harness_runs"` → `parent.parent.parent / "harness_runs"`
    (engine/ -> arunner/ -> repo root). Correct.
  - version path `parent.parent / "arunner" / "__init__.py"` →
    `parent.parent / "__init__.py"` (engine/ -> arunner/__init__.py). Correct.
  Both runtime-verified in items 4 and 7.

## 7. Full suite green — PASS

```
$ python3 -m pytest -q 2>&1 | tail -3
202 passed in 12.38s
```

---

## Working-tree integrity after review
All snapshots restored via `shutil.copy2`. `git diff HEAD --stat` for the two
mutated files shows only the intended 13a deltas (pyproject 6 lines, plugin.json 2
lines); no residue. pycache was purged before the post-restore plugin re-verify.

---

VERDICT: SHIP
