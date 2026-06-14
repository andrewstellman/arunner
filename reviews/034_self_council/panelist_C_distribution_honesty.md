# Panelist C — Distribution Honesty & Consistency (Iteration 13a)

Repo: `arunner` @ `/Users/andrewstellman/Documents/wakecycle`, git `main`, work UNCOMMITTED.
Reviewer C — adversarial honesty. Evidence quoted from on-disk files + live runs.

---

## 1. NPM PACKAGE HONESTY — PASS

`npm-bin/arunner.js` is a thin launcher, NOT a Node reimplementation. It probes
`python3`/`python`, imports `arunner`, and execs `python -m arunner` with args
passed through:

```js
const probe = spawnSync(py, ["-c", "import arunner"], { stdio: "ignore" });
if (probe.error || probe.status !== 0) continue;
const run = spawnSync(py, ["-m", "arunner", ...args], { stdio: "inherit" });
```

It points users at pipx when Python/package is absent and exits non-zero:

```js
const HINT =
  "arunner's engine is a Python package and was not found.\n" +
  ...
  "  pipx install arunner            # recommended\n" +
  "  python3 -m pip install arunner\n" +
  "(The npm package is only a thin launcher for the Python CLI.)";
...
process.exit(127);
```

It explicitly disclaims standalone-Node-CLI status (lines 8, 10):
"It deliberately does NOT reimplement the CLI in Node" / "it never pretends to
be a working standalone Node CLI."

LIVE DELEGATION VERIFIED:
```
$ node npm-bin/arunner.js --version
arunner 0.1.0       (exit=0)
```
It really execs the Python CLI. No "0.0.1", no placeholder string, no
standalone-CLI claim.

`package.json`: name `arunner`, version `0.1.0`, `"bin": {"arunner": "npm-bin/arunner.js"}`,
`"files": ["npm-bin/", "README.md", "LICENSE"]` — all three paths exist on disk. Sane.

## 2. PLUGIN / MARKETPLACE CONSISTENCY — PASS

`plugins/arunner/.claude-plugin/plugin.json`: `"name": "arunner"`, `"version": "0.1.0"`
(the prior 0.0.1 drift is FIXED).
`.claude-plugin/marketplace.json`: `"name": "arunner"`, and
`"plugins": [{ "name": "arunner", "source": "./plugins/arunner", "category": "productivity" }]`
— source path resolves to the plugin dir. Internally consistent.
SKILL.md frontmatter: `name: arunner`, `version: 0.1.0`. Consistent.

## 3. VERSION / NAME CONSISTENCY — PASS (single-source verified)

| Surface | Quote |
|---|---|
| pyproject.toml | `name = "arunner"` / `version = "0.1.0"` |
| package.json | `"name": "arunner"` / `"version": "0.1.0"` |
| SKILL.md frontmatter | `name: arunner` / `version: 0.1.0` |
| arunner/__init__.py | `__version__ = "0.1.0"` |
| plugin.json | `"name": "arunner"` / `"version": "0.1.0"` |

`tests/test_version_single_source.py` + `tests/test_packaging.py`: **15 passed**.

## 4. STALE / DISHONEST CLAIMS IN DOCS

- Broken-engine-path grep (`bin/tick.py` etc. in README/TOOLKIT/AGENTS/docs/plugins/references):
  **EMPTY** — no doc points at the moved-away `bin/` engine. PASS.
- Stale-claim grep in README/TOOLKIT/AGENTS/skills (`name reservation|placeholder|0.0.1|wire up at v0.1.0`):
  the only hits are the LEGITIMATE prompt-substitution sense of "placeholder"
  (e.g. `{HEARTBEAT_PATH}` tokens) which the charter explicitly tolerates — plus
  README's honest historical note (below). No "wire up at v0.1.0" future-tense
  string anywhere. PASS.
- Console scripts `arunner-ticker` / `arunner-heartbeat` are HONEST: declared in
  pyproject `[project.scripts]` (`arunner-ticker = "arunner.engine.ticker:main"`,
  `arunner-heartbeat = "arunner.engine.heartbeat:main"`) and their `main`
  attributes resolve on import (verified live; `cli.main`, `ticker.main`,
  `heartbeat.main` all `True`). Docs describe them present-tense; not vaporware.
- README:283 "developed under the working name **wakecycle** (the abandoned
  0.0.1 PyPI/npm reservations are under that name); renamed to **arunner** at
  v0.1.0" — this is an HONEST past-tense historical note about the *old*
  wakecycle name, not a stale promise about the current package. Not a defect.

## 5. `arunner/__init__.py` DOCSTRING — PASS

No "pre-release name reservation" language. It describes the real v0.1.0:
"The generic engine ships inside this package at ``arunner.engine`` ... the
lifecycle CLI is ``arunner.cli`` (console script ``arunner``)." `_reserve.py`
is deleted (git status). No reservation language anywhere under `arunner/`.

---

## BLOCKING ISSUE

**B1 — `pyproject.toml` description carries a stale 0.0.1 name-reservation claim
(publish-facing, lands on the PyPI project page).**

`pyproject.toml:8`:
```
description = "A batch orchestrator for AI coding agents that runs inside your existing agent session - no server, no daemon, no admin rights. (0.0.1 reserves the name; the harness ships here shortly.)"
```

This is the exact stale/dishonest claim this iteration was supposed to kill:
- It says "**0.0.1 reserves the name**" — but this IS the v0.1.0 real release;
  the harness does NOT "ship here shortly," it ships HERE, NOW.
- This is the `description` PyPI renders at the top of the project page and in
  `pip search`/`pip show` output — the single most distribution-facing string,
  more visible than any README line.
- Charter item 4 explicitly calls for grepping `0.0.1` out of distribution
  metadata; the README/TOOLKIT/AGENTS were cleaned but the pyproject description
  was missed. It directly contradicts the now-correct `version = "0.1.0"` two
  lines above it.

Fix: drop the parenthetical so the description ends at "...no admin rights."
(Consider also `classifiers = ["Development Status :: 2 - Pre-Alpha"]` — defensible
for a 0.1.0 but mildly in tension with the "real working release" framing; not
blocking, noting for the panel.)

---

VERDICT: FIX-REQUIRED

Blocking:
- B1: `pyproject.toml:8` `description` still claims "0.0.1 reserves the name; the
  harness ships here shortly." — a stale name-reservation/0.0.1 claim on the
  primary (PyPI) distribution channel's most visible field. Remove the
  parenthetical before publish.
