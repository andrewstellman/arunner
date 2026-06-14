# Instruction 034 self-council synthesis — Iteration 13a: real packaging + publish-safety (FR-33/34)

*Mandatory 3-panel release gate. Three fresh-context, role-locked, adversarial reviewers, each verifying on disk (running build/install/smoke, not trusting the implementer). Date: 2026-06-14.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_console_version.md` | console script & version single-source (FR-34) | **SHIP** |
| `panelist_B_publish_safety.md` | publish-safety gates RUN (FR-33), nothing published | **SHIP** |
| `panelist_C_distribution_honesty.md` | npm role honesty + version/name + no stale claims | **FIX-REQUIRED → resolved** |
| `confirm_C_description.md` (confirmation) | C's sole blocker resolved | **SHIP** |

## Outcome: unanimous SHIP (after one fix round)

### Panelist A — Console script & version (SHIP)
Verified live: `[project.scripts]` maps `arunner = arunner.cli:main` (real FR-53 router) plus `arunner-ticker`/`arunner-heartbeat` → the engine mains; the `_reserve` stub is fully retired (gone from the tree; zero dangling refs — the only `_reserve` strings left are negative guard assertions in the drift test). The single source `arunner/__init__.py:__version__ = 0.1.0` is mirrored/read by pyproject, package.json, SKILL frontmatter, plugin.json (bumped 0.0.1→0.1.0), and the engine banner — no divergent literals. `python -m arunner --version` → `arunner 0.1.0`; `tick._arunner_version()` → 0.1.0. The drift test was rewritten value-agnostic and **bites** (scripts→`_reserve` fails the console-script test; plugin.json bump fails its test), restored via `shutil.copy2`. The engine relocation `bin/`→`arunner/engine/` is complete (6 modules + `__init__`; old `bin/` gone) with the `parent.parent`→`parent.parent.parent` runs-root and version-path fixes correct for the deeper nesting. Suite 202 passed.

### Panelist B — Publish-safety (SHIP)
Ran every FR-33 gate independently from the uncommitted tree: (1) clean-clone cold build (rsync to a pristine dir, `python -m build`) → twine check PASSED sdist+wheel; the wheel **ships the full engine** (`arunner/engine/*` + `__init__` + `cli.py`) and `entry_points.txt` declares all three console scripts. (2) throwaway venv installed the **wheel** and the **installed** console scripts smoked clean: `arunner 0.1.0`; the bundled `demo_shell.json` (concretized, pool 2) drove to `done` in 3 ticks (completed=3/failed=0, zero API spend); `status`+`summary` rc 0/non-empty; `arunner-heartbeat emit`+`terminal --result-file` rc 0 with 2 valid JSON lines (and the missing-`--result-file` negative control correctly rc≠0). (3) npm `--dry-run` packed exactly 4 files (LICENSE, README.md, npm-bin/arunner.js, package.json), name arunner, v0.1.0, no upload. (4) **Nothing published** — no `twine upload`, no real `npm publish`.

### Panelist C — Distribution honesty (FIX-REQUIRED → resolved)
Confirmed: the npm launcher is honest (a thin Python-exec launcher — `node npm-bin/arunner.js --version` really printed `arunner 0.1.0`; disclaims standalone-Node-CLI status; points at `pipx install arunner`; no `0.0.1`/placeholder string). Version/name consistent at arunner/0.1.0 across pyproject, package.json, SKILL, `__init__`, plugin.json (the 0.0.1 plugin drift is fixed). The broken-`bin/`-path grep is empty; the `arunner-ticker`/`arunner-heartbeat` console scripts are really declared; `__init__` no longer claims a name reservation.

**Sole blocker (genuine catch):** `pyproject.toml:8` `description` still carried `"(0.0.1 reserves the name; the harness ships here shortly.)"` — which renders on the PyPI project page and contradicts the real v0.1.0.

**Fix:** removed the stale parenthetical from the description. A fresh confirmation reviewer verified the description now reads plainly with no `0.0.1`/reservation/placeholder language, that the only remaining such string is README's honest wakecycle→arunner lineage note, and that the TOML still parses → **SHIP**.

## Net
Iteration 13a ships v0.1.0 packaging: the engine moved into the package so the installed wheel works, the real `arunner` (+`arunner-ticker`/`arunner-heartbeat`) console scripts replace the retired `_reserve` stub, the FR-34 single source drives every surface (drift test rewritten + biting), the npm package is an honest thin launcher, and all FR-33 publish-safety gates (cold build → twine check → throwaway-venv install + demo-to-done smoke → npm dry-run) were RUN and pass with **nothing published**. Suite 193→202.
