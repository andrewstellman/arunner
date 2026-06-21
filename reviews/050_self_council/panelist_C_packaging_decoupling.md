# Panelist C — packaging & decoupling (FR-62 Textual TUI)

**Charter:** Textual gated behind an optional `[tui]` extra; the bare engine
install stays dependency-free and importable WITHOUT Textual; `arunner monitor`
remains the always-available zero-dependency fallback.

**Empirical results (all green):**
- `import arunner.cli, arunner.engine.tick, arunner.tui.data` → `'textual' in
  sys.modules` is **False** — and critically, **textual 8.2.7 IS installed in
  this env**, so this proves true lazy decoupling, not a false pass from an
  absent dependency.
- `python3 -m pytest tests/test_tui.py tests/test_packaging.py -q` → **24 passed**.
- `grep -rn textual arunner/engine/` → **no matches**. Engine package is
  Textual-free.
- `arunner.cli.main(['--help'])` runs to completion with `'textual' in
  sys.modules` still **False**.

## Findings (all non-blocking, PASS)

1. **`pyproject.toml`** declares `[project.optional-dependencies] tui =
   ["textual>=0.50"]`; base `[project]` has zero runtime deps and no Textual. The
   setuptools packages list includes `"arunner.tui"`, so the wheel ships it.
   Guarded by `test_tui_extra_declared_in_pyproject` + `test_packaging.py`.

2. **Textual is imported in exactly one place** — `arunner/tui/app.py` top-level
   (acceptable, since the module is only reached lazily). The *only* import of
   `arunner.tui.app` is the lazy one inside `cmd_tui`. `arunner/tui/__init__.py`
   imports nothing; `arunner/tui/data.py` imports only `arunner.cli` (stdlib). No
   eager path from the bare CLI reaches `app.py`.

3. **`_DISPATCH` references the `cmd_tui` function object**, not `app.py`, so
   building the parser/dispatch table stays Textual-free — confirmed via `--help`.

4. **Clean degradation:** `cmd_tui` wraps the lazy import in `try/except
   ImportError`, prints `pip install 'arunner[tui]'` **and** points at the
   `arunner monitor` stdlib fallback, returns exit code **3** (non-crash).
   Verified by `test_tui_degrades_cleanly_when_textual_absent` (poisons
   `sys.modules['textual']=None`, asserts rc==3 + both messages). Non-run-dir
   returns 2.

5. **`arunner monitor` is unchanged stdlib** and still the zero-dep fallback. The
   TUI data layer reuses it via the shared call path
   (`data.run_view_frame` → `CLI.render_monitor_frame` → `tick._format_table`),
   pinned, so the TUI cannot drift from the fallback.

6. **`test_engine_path_has_no_textual_import`** does the no-leak check in a real
   clean **subprocess** with explicit PYTHONPATH — a genuine import-graph
   assertion.

No import chain from the bare CLI to Textual exists. Installing without the
`[tui]` extra leaves every non-tui verb fully functional; only `arunner tui`
needs the extra and degrades cleanly without it.

VERDICT: SHIP
