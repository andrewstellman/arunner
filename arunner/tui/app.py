"""FR-62 Textual VIEW LAYER -- the interactive `arunner tui` app.

This module is the ONLY place Textual is imported, and it is imported LAZILY
(from ``cli.cmd_tui``) only when ``arunner tui`` actually runs. So a bare
``arunner`` install with no `[tui]` extra never imports Textual, and the
engine/ticker/monitor path stays dependency-free (NFR-3).

Everything the views render comes from the strictly read-only
``arunner.tui.data`` layer (which reuses the FR-59 monitor render path). The app
holds NO write path of its own: it advances nothing, locks nothing, drops no
control file -- it is a viewer over externalized disk state (NFR-9), the same
property the FR-59 monitor holds.

Four views (all read-only):
  1. Run picker     -- run-dirs newest-first; pick one to open.
  2. Run view       -- the live status table (FR-59 renderer), refreshing.
  3. Entry view     -- one entry's full record + heartbeat history + results.
  4. Log/HB tail    -- follow that entry's heartbeat.ndjson (and the journal).
"""
from __future__ import annotations

from pathlib import Path

# Textual is the optional `[tui]` extra. Importing app.py REQUIRES it; the
# engine path never imports this module (cli.cmd_tui imports it lazily and
# prints a clean install hint if Textual is absent).
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from arunner.tui import data as DATA

# The display refresh cadence (seconds). Like the FR-59 monitor: this refreshes
# the DISPLAY -- the freshness header makes clear that lifecycle/counts are only
# as fresh as the last engine tick, while ACTIVITY/HB-AGE are live.
REFRESH_SECONDS = 2.0


class RunPickerScreen(Screen):
    """View 1: list run-dirs under the runs-root, newest-first; pick one."""

    BINDINGS = [Binding("r", "refresh", "Refresh"), Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Pick a run (Enter to open):  %s" % self.app.runs_root,
                    id="picker-title")
        yield ListView(id="run-list")
        yield Footer()

    def on_mount(self) -> None:
        self._reload()

    def action_refresh(self) -> None:
        self._reload()

    def _reload(self) -> None:
        lv = self.query_one("#run-list", ListView)
        lv.clear()
        runs = DATA.list_runs(self.app.runs_root)
        if not runs:
            lv.append(ListItem(Label("(no runs under %s)" % self.app.runs_root)))
            return
        for run in runs:
            item = ListItem(Label(DATA.format_picker_row(run)))
            item.run_dir = run["run_dir"]                       # carry the path
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        run_dir = getattr(event.item, "run_dir", None)
        if run_dir is not None:
            self.app.push_screen(RunViewScreen(run_dir))


class RunViewScreen(Screen):
    """View 2: the live status table (FR-59 renderer) + an entry list to drill
    into. Refreshes on an interval; exits the loop when the run is terminal only
    in the sense that the header stops advancing (we keep rendering, read-only)."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, run_dir) -> None:
        super().__init__()
        self.run_dir = Path(run_dir)
        self._last_good = "(waiting for run state...)"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self._last_good, id="run-table")
        yield Label("Entries (Enter to drill in):", id="entries-title")
        yield ListView(id="entry-list")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.run_dir.name
        self._refresh_table()
        self._reload_entries()
        self.set_interval(REFRESH_SECONDS, self._refresh_table)

    def action_refresh(self) -> None:
        self._refresh_table()
        self._reload_entries()

    def _refresh_table(self) -> None:
        text, _terminal, ok = DATA.run_view_frame(self.run_dir,
                                                  interval=REFRESH_SECONDS)
        if ok:
            self._last_good = text
        self.query_one("#run-table", Static).update(self._last_good)

    def _reload_entries(self) -> None:
        lv = self.query_one("#entry-list", ListView)
        lv.clear()
        for name in DATA.entry_names(self.run_dir):
            item = ListItem(Label(name))
            item.entry_name = name
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        name = getattr(event.item, "entry_name", None)
        if name is not None:
            self.app.push_screen(EntryViewScreen(self.run_dir, name))


class EntryViewScreen(Screen):
    """View 3: one entry's full record + its heartbeat history + results."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("t", "tail", "Tail log"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, run_dir, entry_name) -> None:
        super().__init__()
        self.run_dir = Path(run_dir)
        self.entry_name = entry_name

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="entry-detail")
            yield Static("", id="entry-history")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "%s / %s" % (self.run_dir.name, self.entry_name)
        self._refresh()
        self.set_interval(REFRESH_SECONDS, self._refresh)

    def action_refresh(self) -> None:
        self._refresh()

    def action_tail(self) -> None:
        self.app.push_screen(TailScreen(self.run_dir, self.entry_name))

    def _refresh(self) -> None:
        detail = DATA.entry_detail(self.run_dir, self.entry_name)
        history = DATA.heartbeat_history(self.run_dir, self.entry_name)
        self.query_one("#entry-detail", Static).update(
            DATA.format_entry_detail(detail))
        self.query_one("#entry-history", Static).update(
            "heartbeat history:\n" + DATA.format_history(history))


class TailScreen(Screen):
    """View 4: follow this entry's heartbeat.ndjson and the run journal live."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, run_dir, entry_name) -> None:
        super().__init__()
        self.run_dir = Path(run_dir)
        self.entry_name = entry_name

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("heartbeat.ndjson (%s):" % self.entry_name)
            yield Static("", id="hb-tail")
            yield Label("journal.ndjson (run):")
            yield Static("", id="journal-tail")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "tail %s / %s" % (self.run_dir.name, self.entry_name)
        self._refresh()
        self.set_interval(REFRESH_SECONDS, self._refresh)

    def _refresh(self) -> None:
        hb = DATA.heartbeat_history(self.run_dir, self.entry_name, limit=40)
        jr = DATA.journal_tail(self.run_dir, limit=40)
        self.query_one("#hb-tail", Static).update(DATA.format_history(hb, 40))
        self.query_one("#journal-tail", Static).update(
            DATA.format_history(jr, 40))


class ArunnerTUI(App):
    """The `arunner tui` app. Strictly read-only: it constructs no write path.
    Opens the run picker, or jumps straight to the run view when launched with a
    run-dir argument."""

    TITLE = "arunner tui"
    CSS = "#run-table { height: auto; } #picker-title, #entries-title { padding: 0 1; }"

    def __init__(self, runs_root=None, run_dir=None) -> None:
        super().__init__()
        self.runs_root = (Path(runs_root) if runs_root is not None
                          else DATA.default_runs_root())
        self._initial_run_dir = Path(run_dir) if run_dir is not None else None

    def on_mount(self) -> None:
        if self._initial_run_dir is not None:
            self.push_screen(RunViewScreen(self._initial_run_dir))
        else:
            self.push_screen(RunPickerScreen())


def run(runs_root=None, run_dir=None) -> int:
    """Launch the TUI. Returns a process exit code (0)."""
    ArunnerTUI(runs_root=runs_root, run_dir=run_dir).run()
    return 0
