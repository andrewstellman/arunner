"""FR-62 -- the optional, decoupled, strictly read-only Textual TUI.

`arunner tui` lets an operator pick a run, watch it live, drill into one entry's
record, and tail that entry's heartbeat/journal stream. It is an evolution of
the FR-59 monitor: a fully decoupled, read-only consumer of externalized disk
state, whose Textual dependency never touches the stdlib-only engine.

MUTATION PINS (instr 050):
  * test_never_writes -- the load-bearing safety property (same as FR-59): the
    TUI's DATA LAYER, driven over a fixture run-dir, creates/modifies NOTHING --
    no run-state write, no `.tick.lock`, no control file. Making the data layer
    write must turn this red (snapshot before/after).
  * test_run_view_reuses_renderer_no_fork -- the run-view table IS the FR-59
    monitor's `_format_table` + state-loader (shared CALL PATH via
    `cli.render_monitor_frame`, not a copy), so the TUI can't drift from
    `monitor`.
  * test_engine_path_has_no_textual_import -- the engine/ticker/monitor + data
    layer import path pulls in zero Textual (importable on a bare install);
    `arunner tui` degrades cleanly with a helpful message when Textual is absent.

The Textual-driven UI is exercised headless via the data layer + the pure
view-model formatters (no pixel assertions).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import arunner.cli as CLI
from arunner.tui import data as DATA


def _heartbeat(run_dir, run, status="IN_PROGRESS", label="step 1"):
    hb = Path(run_dir) / run / "heartbeat.ndjson"
    hb.parent.mkdir(parents=True, exist_ok=True)
    with hb.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": "2026-06-15T00:00:00Z", "task_id": run,
                             "status": status, "label": label}) + "\n")


def _run_dir(done=False, with_result=False):
    """A minimal STATIC run-dir (no live workers) so the never-writes pin is not
    confounded by detached workers still writing. run-01 is running with a
    heartbeat + manifest; run-02 is queued. Optionally a terminal results/
    record for run-01 + a journal line."""
    rd = Path(tempfile.mkdtemp())
    runs = {"run-01": {"task_id": "a", "job_id": "job-00001", "target_repo": "/r/a",
                       "state": "completed" if done else "running",
                       "last_hb_status": "COMPLETED" if done else "IN_PROGRESS",
                       "claimed_at": 1.0},
            "run-02": {"task_id": "b", "job_id": "job-00002", "target_repo": "/r/b",
                       "state": "queued", "last_hb_status": None, "claimed_at": None}}
    counts = {"queued": 0 if done else 1, "claimed": 0, "running": 0 if done else 1,
              "stalled": 0, "completed": 2 if done else 0, "failed": 0,
              "auth_or_launch_failed": 0, "abandoned": 0}
    status = {"cycle": 3, "pool_size": 2, "counts": counts, "done": done,
              "runs": runs, "last_tick_wall": 1000.0}
    (rd / "harness_status.json").write_text(json.dumps(status), encoding="utf-8")
    plan = {"pool_size": 2, "entries": [
        {"task_id": "a", "target_repo": "/r/a", "dispatch_mode": "shell",
         "adapter": "wrap", "command": ["x"]},
        {"task_id": "b", "target_repo": "/r/b", "dispatch_mode": "subagent"}]}
    (rd / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    # per-run manifests (where dispatch_mode lives)
    for name, mode in (("run-01", "shell"), ("run-02", "subagent")):
        (rd / name).mkdir(exist_ok=True)
        (rd / name / "manifest.json").write_text(json.dumps(
            {"task_id": runs[name]["task_id"], "target_repo": runs[name]["target_repo"],
             "dispatch_mode": mode, "run": name, "job_id": runs[name]["job_id"]}),
            encoding="utf-8")
    _heartbeat(rd, "run-01", "IN_PROGRESS", "step 1")
    if with_result:
        (rd / "results").mkdir(exist_ok=True)
        (rd / "results" / "result-00001.json").write_text(json.dumps(
            {"job_id": "job-00001", "status": "COMPLETED",
             "result_file": "/r/a/OUT.md", "summary": "did the thing",
             "reaped_ts": "2026-06-15T00:05:00Z"}), encoding="utf-8")
        (rd / "journal.ndjson").write_text(
            json.dumps({"ts": "2026-06-15T00:05:00Z", "tick": 3, "type": "verdict",
                        "verdict": "CONTINUE"}) + "\n", encoding="utf-8")
    return rd


def _snapshot(rd):
    out = {}
    for p in sorted(Path(rd).rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(rd))] = (st.st_mtime_ns, st.st_size,
                                           hash(p.read_bytes()))
    return out


def _tui_args(run_dir=None, runs_root=None):
    return argparse.Namespace(run_dir=str(run_dir) if run_dir else None,
                              runs_root=str(runs_root) if runs_root else None)


class NeverWrites(unittest.TestCase):                           # PIN

    def test_never_writes(self):
        rd = _run_dir(with_result=True)
        # a sibling run-dir under a shared root, so list_runs is exercised too
        root = rd.parent
        before_rd = _snapshot(rd)
        before_root = sorted(str(p) for p in root.rglob("*"))

        # drive the WHOLE read-only data layer, several passes
        for _ in range(3):
            DATA.list_runs(root)
            DATA.run_view_frame(rd, interval=2.0, now=2000.0)
            for name in DATA.entry_names(rd):
                DATA.entry_detail(rd, name)
                DATA.heartbeat_history(rd, name)
            DATA.journal_tail(rd)
            DATA.tail_lines(rd / "run-01" / "heartbeat.ndjson")

        self.assertEqual(before_rd, _snapshot(rd), "TUI data layer mutated the run-dir")
        self.assertEqual(before_root, sorted(str(p) for p in root.rglob("*")),
                         "TUI data layer created/removed files under the runs-root")
        self.assertFalse((rd / ".tick.lock").exists(), "data layer took .tick.lock")
        for ctrl in ("STOP", "PAUSE", "RESUME", "CANCEL", "POOL", "CADENCE",
                     "POLL-NOW"):
            self.assertFalse((rd / ctrl).exists(),
                             "data layer dropped a %s control file" % ctrl)

    def test_list_runs_does_not_create_missing_root(self):
        missing = Path(tempfile.mkdtemp()) / "nope"
        self.assertEqual(DATA.list_runs(missing), [])
        self.assertFalse(missing.exists(), "list_runs created a missing runs-root")


class RendererReuse(unittest.TestCase):                         # PIN

    def test_run_view_reuses_renderer_no_fork(self):
        rd = _run_dir()
        status = json.loads((rd / "harness_status.json").read_text())
        plan = json.loads((rd / "plan.json").read_text())
        expected = CLI.TICK._format_table(rd, status, plan, terminal=False)
        text, terminal, ok = DATA.run_view_frame(rd, interval=2.0, now=2000.0)
        self.assertTrue(ok)
        # the frame is the monitor-owned freshness header + the SHARED table
        self.assertTrue(text.endswith(expected),
                        "TUI run-view table diverged from _format_table")
        self.assertIn("monitor: refresh", text.split("\n", 1)[0])

    def test_run_view_delegates_to_monitor_call_path(self):
        rd = _run_dir()
        calls = []
        orig = CLI.render_monitor_frame
        CLI.render_monitor_frame = lambda *a, **k: (calls.append((a, k)) or
                                                    orig(*a, **k))
        try:
            DATA.run_view_frame(rd, interval=2.0, now=2000.0)
        finally:
            CLI.render_monitor_frame = orig
        self.assertEqual(len(calls), 1,
                         "run_view_frame must route through cli.render_monitor_frame")


class ExtraGatingDecoupling(unittest.TestCase):                 # PIN

    def test_engine_path_has_no_textual_import(self):
        # importing the engine/CLI/monitor + the TUI DATA layer must NOT import
        # Textual (it lives only in arunner.tui.app, imported lazily). Run in a
        # clean subprocess so it's a true import-graph check.
        code = (
            "import sys\n"
            "import arunner.cli, arunner.engine.tick, arunner.tui.data\n"
            "assert 'textual' not in sys.modules, "
            "'Textual leaked onto the engine/monitor/data import path'\n"
            "print('ok')\n"
        )
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ok", r.stdout)

    def test_tui_degrades_cleanly_when_textual_absent(self):
        rd = _run_dir()
        # simulate a bare install: poison the textual import so `from arunner.tui
        # import app` raises ImportError, exactly as it would with no [tui] extra.
        saved = {k: sys.modules.get(k) for k in
                 ("textual", "textual.app", "arunner.tui.app")}
        sys.modules["textual"] = None                  # -> ImportError on import
        sys.modules.pop("arunner.tui.app", None)
        sys.modules.pop("textual.app", None)
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                rc = CLI.cmd_tui(_tui_args(run_dir=rd))
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        self.assertEqual(rc, 3)
        self.assertIn("arunner[tui]", err.getvalue())
        self.assertIn("monitor", err.getvalue())       # points at the fallback

    def test_tui_rejects_non_run_dir(self):
        empty = Path(tempfile.mkdtemp())               # no harness_status.json
        err = io.StringIO()
        with redirect_stderr(err):
            rc = CLI.cmd_tui(_tui_args(run_dir=empty))
        self.assertEqual(rc, 2)
        self.assertIn("not a run-dir", err.getvalue())

    def test_tui_extra_declared_in_pyproject(self):
        txt = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
        self.assertIn("tui = [", txt)                  # optional extra exists
        self.assertIn("textual", txt)
        self.assertIn('"arunner.tui"', txt)            # package ships in the wheel


class DataLayerViewModels(unittest.TestCase):

    def test_list_runs_newest_first_with_summary(self):
        root = Path(tempfile.mkdtemp())
        # two runs; bump the second's mtime so it sorts first
        a = _run_dir(); b = _run_dir(done=True)
        (root / "run-a").mkdir(); (root / "run-b").mkdir()
        # move fixtures under the shared root by symlink-free copy of status only
        for src, name, newer in ((a, "run-a", False), (b, "run-b", True)):
            dst = root / name
            (dst / "harness_status.json").write_text(
                (src / "harness_status.json").read_text())
            t = 2000.0 if newer else 1000.0
            os.utime(dst / "harness_status.json", (t, t))
        runs = DATA.list_runs(root)
        self.assertEqual([r["name"] for r in runs], ["run-b", "run-a"])
        self.assertTrue(runs[0]["done"])
        self.assertEqual(runs[1]["cycle"], 3)
        self.assertEqual(runs[0]["counts"]["completed"], 2)

    def test_list_runs_surfaces_unreadable_status(self):
        root = Path(tempfile.mkdtemp())
        bad = root / "broken"; bad.mkdir()
        (bad / "harness_status.json").write_text("{ not json")
        runs = DATA.list_runs(root)
        self.assertEqual(len(runs), 1)
        self.assertFalse(runs[0]["ok"])
        self.assertIn("unreadable", DATA.format_picker_row(runs[0]))

    def test_entry_detail_full_record(self):
        rd = _run_dir(with_result=True)
        d = DATA.entry_detail(rd, "run-01")
        self.assertEqual(d["state"], "running")
        self.assertEqual(d["target_repo"], "/r/a")
        self.assertEqual(d["dispatch_mode"], "shell")    # from manifest.json
        self.assertEqual(d["claimed_at"], 1.0)
        self.assertEqual(d["activity"], "step 1")        # live heartbeat label
        self.assertTrue(d["terminal"])                   # has a results/ record
        self.assertEqual(d["result"]["result_file"], "/r/a/OUT.md")

    def test_entry_detail_missing_entry_is_none(self):
        rd = _run_dir()
        self.assertIsNone(DATA.entry_detail(rd, "run-99"))

    def test_heartbeat_history_parses_and_keeps_malformed(self):
        rd = _run_dir()
        hb = rd / "run-01" / "heartbeat.ndjson"
        with hb.open("a", encoding="utf-8") as fh:
            fh.write("{ not json\n")
            fh.write(json.dumps({"ts": "t2", "status": "IN_PROGRESS",
                                 "label": "step 2"}) + "\n")
        hist = DATA.heartbeat_history(rd, "run-01")
        self.assertEqual(hist[-1]["label"], "step 2")
        self.assertTrue(any("_raw" in h for h in hist))   # malformed surfaced
        rendered = DATA.format_history(hist)
        self.assertIn("step 2", rendered)
        self.assertIn("!", rendered)                      # malformed marker

    def test_format_entry_detail_text(self):
        rd = _run_dir(with_result=True)
        txt = DATA.format_entry_detail(DATA.entry_detail(rd, "run-01"))
        self.assertIn("Entry run-01", txt)
        self.assertIn("dispatch_mode : shell", txt)
        self.assertIn("results/ record", txt)
        self.assertIn("did the thing", txt)

    def test_format_picker_row_live_and_done(self):
        rd = _run_dir(done=True)
        run = DATA.list_runs(rd.parent)[0]
        self.assertIn("DONE", DATA.format_picker_row(run))

    def test_journal_tail(self):
        rd = _run_dir(with_result=True)
        jt = DATA.journal_tail(rd)
        self.assertEqual(jt[-1]["verdict"], "CONTINUE")

    def test_default_runs_root_honors_env(self):
        saved = os.environ.get("ARUNNER_RUNS_DIR")
        os.environ["ARUNNER_RUNS_DIR"] = "/tmp/some-runs"
        try:
            self.assertEqual(DATA.default_runs_root(), Path("/tmp/some-runs"))
        finally:
            if saved is None:
                os.environ.pop("ARUNNER_RUNS_DIR", None)
            else:
                os.environ["ARUNNER_RUNS_DIR"] = saved


if __name__ == "__main__":
    unittest.main()
