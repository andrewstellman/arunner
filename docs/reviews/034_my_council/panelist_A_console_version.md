# Panelist A — CONSOLE SCRIPT & VERSION SINGLE-SOURCE

**Iteration:** 13a (real packaging) · **HEAD:** `6dc8016` (verified at mount; matches the SHA under review)
**Charter:** Console script wiring + version single-source. Adversarial; verified against built/installed artifact, not worker claims.

## VERDICT: **SHIP**

Every claim in the charter holds against the actual code AND against a freshly built wheel installed into a throwaway venv. The console script resolves to the real CLI router, `_reserve` is fully retired with zero dangling references in `.py`/`.toml`, the version single-source drives every surface, and the rewritten drift test BITES (mutation-verified). `arunner --version` (installed) prints `arunner 0.1.0`.

---

## Findings

### 1. Console script wiring → REAL CLI router, not a stub — **PASS**

- `pyproject.toml:27-30` `[project.scripts]`:
  ```
  arunner = "arunner.cli:main"
  arunner-ticker = "arunner.engine.ticker:main"
  arunner-heartbeat = "arunner.engine.heartbeat:main"
  ```
- `arunner/cli.py:235-240` `main()` is a real router (`argparse` subparsers → `_DISPATCH`), NOT a stub. Verbs implemented as thin wrappers over tested engine entry points: run/status/stop/resume/summary/new/expand/preview (`cli.py:82-192`, `_DISPATCH` at `cli.py:230-232`). `--version` wired at `cli.py:197` reading `__version__` (imported `cli.py:31`).
- **Built-artifact evidence** (best evidence): built the wheel into a throwaway venv, installed it, ran the installed console script:
  - `python -m build --wheel` → `Successfully built arunner-0.1.0-py3-none-any.whl`
  - wheel `entry_points.txt`:
    ```
    [console_scripts]
    arunner = arunner.cli:main
    arunner-heartbeat = arunner.engine.heartbeat:main
    arunner-ticker = arunner.engine.ticker:main
    ```
  - installed shim `/tmp/av/bin/arunner` contains `from arunner.cli import main` — resolves to the real router, not `_reserve`.
  - `/tmp/av/bin/arunner --help` lists all eight verbs `{run,status,stop,summary,resume,new,expand,preview}`.
  - **End-to-end, not just help:** installed `arunner expand /tmp/sh.json --out /tmp/exp.json` → exit 0, produced a valid expanded plan with 1 entry. The installed console script executes real engine work, confirming the engine ships inside the wheel (`packages = ["arunner", "arunner.engine"]`, `pyproject.toml:33`) and is reachable from the installed script.

### 2. `_reserve.py` fully retired, no dangling references — **PASS**

- `grep -rn "_reserve" … --include=*.py --include=*.toml` returns hits ONLY in `tests/test_version_single_source.py` — all of which are the retirement *guard itself* (docstring line 7; `assertNotIn("_reserve", pyproject)` line 75; `assertFalse(.../"_reserve.py").exists()` line 76; method name `test_console_script_is_the_real_cli_not_reserve` line 70). Zero hits in `pyproject.toml`, `cli.py`, or any engine source. (Other matches are in `reviews/` and `docs/` historical text, which are out of scope per the charter.)
- `arunner/_reserve.py` does not exist (the installed wheel contains `arunner/cli.py`, no `_reserve.py`).
- No `arunner._reserve:main` reference survives anywhere a release surface reads.

### 3. Version single-source drives every surface — **PASS**

Single source: `arunner/__init__.py:9` → `__version__ = "0.1.0"`.

Mirrors (literal, asserted equal to canonical by the drift test):
- `pyproject.toml:7` `version = "0.1.0"` — guarded by `test_pyproject_mirrors_canonical`.
- `package.json:3` `"version": "0.1.0"` — guarded by `test_package_json_mirrors_canonical`.
- `plugins/arunner/skills/arunner/SKILL.md` frontmatter — guarded by `test_skill_frontmatter_mirrors_canonical`.
- `plugins/arunner/.claude-plugin/plugin.json` — guarded by `test_plugin_json_mirrors_canonical` (the surface that had drifted to 0.0.1; now mirrored).

Readers (no hardcoded literal — read `__version__` at runtime):
- CLI banner / `--version`: `cli.py:31` imports `__version__`, `cli.py:197` emits `"arunner %s" % __version__`. Installed `arunner --version` → `arunner 0.1.0`.
- `tick.py --init` banner: `tick.py:1410-1412` prints `"arunner %s" % _arunner_version()` to stderr; `_arunner_version()` (`tick.py:1230-1242`) reads `arunner/__init__.py:__version__` by path.
- Ticker startup: `ticker.py:280-281` prints `"arunner %s" % engine._arunner_version()` — reuses the same single-source reader.
- Skill banner: SKILL frontmatter mirrors and is drift-guarded (above).

**The drift test was REWRITTEN and BITES — mutation-verified.** The pre-13a test asserted `_reserve` read the version; the current `tests/test_version_single_source.py` is value-agnostic (`_canonical()` lines 29-34 reads `__version__`; every assertion compares a *separately-read* mirror to it — not a tautology, since each mirror is parsed from its own file via independent regex/json, not derived from `__version__`).
- Mutation (against the /tmp copy only — real repo untouched): changed `pyproject.toml` `version = "0.1.0"` → `"0.9.9"`. Result:
  ```
  E  AssertionError: '0.9.9' != '0.1.0'
  tests/test_version_single_source.py:49
  FAILED ...::test_pyproject_mirrors_canonical — 1 failed
  ```
  Restored → 1 passed. The assertion is real and fires on divergence.
- Full suite slice `pytest tests/ -k "version or drift or banner" -q` → **13 passed, 8 subtests passed** at HEAD `6dc8016`.
- The test also includes a runtime guard `test_console_script_prints_canonical` (loads `cli.py`, runs `main(["--version"])`, asserts stdout `== "arunner %s" % canon`) and `test_bin_scripts_read_canonical` (asserts `tick._arunner_version() == canon`). Both pass — they would fail if any reader hardcoded a literal that drifted.

### 4. Installed `arunner --version` prints `arunner 0.1.0` — **PASS**

`/tmp/av/bin/arunner --version` → `arunner 0.1.0` (exact). Matches `__init__.__version__`, `pyproject`, `package.json`.

---

## Cleanup

`/tmp/av`, `/tmp/arsrc`, and temp plan files removed (`ls` confirms No such file or directory). No residue.

## Notes / non-blocking observations

- `arunner-ticker --version` is NOT wired as an argparse `--version` flag (it errors to its usage banner). Not a finding: the ticker emits its version banner on startup to stderr (`ticker.py:281`), which is the documented surface; `--version` parity across the secondary console scripts isn't in the FR-34 contract. Worth a one-line backlog note only.
- No version literal appears in any reader path — verified by grep across `arunner/engine/`. The only `version` literals outside the single source are the four mirrors, all drift-guarded.
