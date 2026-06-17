"""arunner.tui -- FR-62: the optional, decoupled, strictly read-only Textual TUI.

The headline UX: `arunner tui [<run-dir>]` -- choose a run, monitor it live,
drill into one entry's record, and tail that entry's heartbeat/journal stream.

**The decoupling that makes the dependency safe (load-bearing):** this package
is split in two so Textual never touches the stdlib-only engine path --

  * ``arunner.tui.data`` -- the read-only DATA LAYER. Pure stdlib; imports
    nothing from Textual. It reuses the FR-59 monitor's render path and the
    engine's on-disk records, and it NEVER writes (the same property FR-59
    holds). This is the module the tests pin (never-writes, renderer-reuse).
  * ``arunner.tui.app`` -- the Textual VIEW LAYER. Imports Textual lazily, only
    when ``arunner tui`` actually runs, so a bare ``arunner`` install (no `[tui]`
    extra) stays dependency-free and the engine/ticker/monitor import path has
    zero Textual import.

So the engine is stdlib (NFR-3); the TUI is an optional, decoupled VIEWER on top
of the externalized disk state -- "just another consumer" (NFR-9), like the
FR-59 monitor, but richer.
"""
