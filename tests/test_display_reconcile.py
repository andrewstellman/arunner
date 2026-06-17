"""instr-051 -- display-correctness reconciliation + TUI Phase-2.

The bug this fixes (it misled the operator all of 2026-06-17): the renderer
showed the per-entry STATE from the persisted ``harness_status.json``, which is
only as fresh as the LAST tick. When the orchestrator is blocked between ticks,
a worker whose heartbeat already says COMPLETED still showed as ``claimed``, and
a live worker with a fresh IN_PROGRESS heartbeat showed as ``claimed`` with no
activity. The fix reconciles the persisted state with the live heartbeat in the
SHARED render path (monitor + tui), strictly read-only.

MUTATION PINS:
  * test_table_reconciles_completed / test_table_reconciles_running -- the
    status/monitor table shows the live truth (``completed*`` / ``running*``);
    neutralizing ``_reconcile_state`` (the revert) makes the stale ``claimed``
    reappear -> these go red.
  * test_data_layer_reconciles_entry -- the TUI entry view reconciles too.
  * test_only_kill_writes -- the read-only boundary: every view writes nothing;
    ONLY ``write_kill_control`` writes, and ONLY a control file.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import arunner.cli as CLI
from arunner.cli import TICK, render_monitor_frame
from arunner.tui import data as DATA


def _mk_run(entries, *, done=False, last_tick_wall=1000.0,
            next_tick_minutes=None, plan_extra=None):
    """Build a static run-dir. `entries` is a list of dicts:
      {name, state, hb_status (or None), hb_label, hb (write a heartbeat?)}.
    """
    rd = Path(tempfile.mkdtemp())
    runs, plan_entries = {}, []
    counts = {"queued": 0, "claimed": 0, "running": 0, "stalled": 0,
              "completed": 0, "failed": 0, "auth_or_launch_failed": 0,
              "abandoned": 0}
    for i, e in enumerate(entries, start=1):
        name = e["name"]
        runs[name] = {"task_id": e.get("task_id", name), "job_id": "job-%05d" % i,
                      "target_repo": e.get("target_repo", "/r/%s" % name),
                      "state": e["state"],
                      "last_hb_status": e.get("last_hb_status"),
                      "claimed_at": e.get("claimed_at", 1.0)}
        counts[e["state"]] = counts.get(e["state"], 0) + 1
        plan_entries.append({"task_id": runs[name]["task_id"],
                             "target_repo": runs[name]["target_repo"],
                             "dispatch_mode": "subagent"})
        (rd / name).mkdir(parents=True, exist_ok=True)
        (rd / name / "manifest.json").write_text(json.dumps(
            {"dispatch_mode": "subagent", "run": name,
             "job_id": runs[name]["job_id"]}), encoding="utf-8")
        if e.get("hb", e.get("hb_status") is not None):
            hb = rd / name / "heartbeat.ndjson"
            with hb.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": "2026-06-17T00:00:00Z", "task_id": name,
                                     "status": e.get("hb_status", "IN_PROGRESS"),
                                     "label": e.get("hb_label", "step 1")}) + "\n")
    status = {"cycle": 4, "pool_size": 4, "counts": counts, "done": done,
              "runs": runs, "last_tick_wall": last_tick_wall}
    if next_tick_minutes is not None:
        status["next_tick_minutes"] = next_tick_minutes
    (rd / "harness_status.json").write_text(json.dumps(status), encoding="utf-8")
    plan = {"pool_size": 4, "entries": plan_entries}
    if plan_extra:
        plan.update(plan_extra)
    (rd / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return rd


def _state_cell(table_text, run_no):
    """The STATE column for run `run_no` from a rendered table (parse the row)."""
    for line in table_text.splitlines():
        if line.startswith("%-5s" % run_no):
            # columns: RUN(5) REPO(22) MODE(8) STATE(13) ...
            return line[5 + 22 + 8: 5 + 22 + 8 + 13].strip()
    return None


class TableReconciliation(unittest.TestCase):                  # PINs

    def test_table_reconciles_completed(self):
        # persisted `claimed`, but the heartbeat already says COMPLETED.
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "COMPLETED", "hb_label": "done"}])
        status = json.loads((rd / "harness_status.json").read_text())
        plan = json.loads((rd / "plan.json").read_text())
        table = TICK._format_table(rd, status, plan, terminal=False)
        self.assertEqual(_state_cell(table, "01"), "completed*")
        self.assertIn("* = live from heartbeat", table)
        # the misleading stale state is NOT shown as the bare STATE
        self.assertNotEqual(_state_cell(table, "01"), "claimed")

    def test_table_reconciles_running(self):
        # persisted `claimed`, fresh IN_PROGRESS heartbeat -> running*.
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "IN_PROGRESS", "hb_label": "step 2"}])
        status = json.loads((rd / "harness_status.json").read_text())
        plan = json.loads((rd / "plan.json").read_text())
        table = TICK._format_table(rd, status, plan, terminal=False)
        self.assertEqual(_state_cell(table, "01"), "running*")

    def test_revert_brings_back_stale_state(self):
        # MUTATION: neutralize the reconciliation (the "revert"); the stale
        # `claimed` must reappear -> proves the pin is load-bearing.
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "COMPLETED"}])
        status = json.loads((rd / "harness_status.json").read_text())
        plan = json.loads((rd / "plan.json").read_text())
        orig = TICK._reconcile_state
        TICK._reconcile_state = lambda persisted, *a, **k: (persisted or "-", False)
        try:
            table = TICK._format_table(rd, status, plan, terminal=False)
        finally:
            TICK._reconcile_state = orig
        self.assertEqual(_state_cell(table, "01"), "claimed")  # the old bug

    def test_monitor_frame_uses_reconciled_table(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "COMPLETED"}])
        text, _term, ok = render_monitor_frame(rd, interval=2.0, now=2000.0)
        self.assertTrue(ok)
        self.assertEqual(_state_cell(text, "01"), "completed*")

    def test_running_persisted_unchanged_no_marker(self):
        # a normal running entry with a live heartbeat is NOT marked (persisted
        # already agrees) -> no false `*`, no churn.
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}])
        status = json.loads((rd / "harness_status.json").read_text())
        plan = json.loads((rd / "plan.json").read_text())
        table = TICK._format_table(rd, status, plan, terminal=False)
        self.assertEqual(_state_cell(table, "01"), "running")
        self.assertNotIn("* = live", table)


class StaleTickHeader(unittest.TestCase):

    def tearDown(self):
        os.environ.pop("ARUNNER_NOW", None)

    def test_stale_tick_flagged(self):
        # cadence 5 min, last tick 30 min ago -> > 2x cadence -> STALE flag.
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}],
                     last_tick_wall=1000.0, next_tick_minutes=5)
        text, _t, ok = render_monitor_frame(rd, interval=2.0, now=1000.0 + 1800)
        self.assertTrue(ok)
        self.assertIn("STALE TICK", text.split("\n", 1)[0])

    def test_not_stale_within_cadence(self):
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}],
                     last_tick_wall=1000.0, next_tick_minutes=5)
        text, _t, ok = render_monitor_frame(rd, interval=2.0, now=1000.0 + 120)
        self.assertNotIn("STALE TICK", text.split("\n", 1)[0])


class DataLayerReconciliation(unittest.TestCase):              # PIN

    def test_data_layer_reconciles_entry(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "COMPLETED", "hb_label": "done"}])
        d = DATA.entry_detail(rd, "run-01")
        self.assertEqual(d["state"], "claimed")            # raw persisted kept
        self.assertEqual(d["display_state"], "completed")  # reconciled
        self.assertTrue(d["live"])
        txt = DATA.format_entry_detail(d)
        self.assertIn("state         : completed", txt)
        self.assertIn("persisted: claimed", txt)

    def test_data_layer_running_persisted_unmarked(self):
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}])
        d = DATA.entry_detail(rd, "run-01")
        self.assertEqual(d["display_state"], "running")
        self.assertFalse(d["live"])


class OverviewHealth(unittest.TestCase):

    NOW = 1_000_000.0

    def _health(self, rd, now=None):
        return DATA.run_health(rd, now=self.NOW if now is None else now)["flag"]

    def test_done(self):
        rd = _mk_run([{"name": "run-01", "state": "completed",
                       "hb_status": "COMPLETED"}], done=True,
                     last_tick_wall=self.NOW)
        self.assertEqual(self._health(rd), "DONE")

    def test_dead_no_tick_past_stall(self):
        # last tick >> 2x stall (45m default -> 90m) ago: orchestrator gone.
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}],
                     last_tick_wall=self.NOW - 3 * 3600)
        self.assertEqual(self._health(rd), "DEAD")

    def test_hung_claimed_no_heartbeat_past_grace(self):
        # claimed, NO heartbeat at all, fresh tick -> dispatched-but-never-started
        rd = _mk_run([{"name": "run-01", "state": "claimed", "hb": False}],
                     last_tick_wall=self.NOW - 60)
        self.assertEqual(self._health(rd), "HUNG?")

    def test_claimed_with_fresh_heartbeat_is_not_hung(self):
        # claimed but a FRESH IN_PROGRESS heartbeat -> alive, not hung (use real
        # `now` so the just-written heartbeat is fresh).
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "IN_PROGRESS"}], last_tick_wall=TICK._now())
        self.assertEqual(DATA.run_health(rd)["flag"], "RUNNING")

    def test_stale_tick(self):
        # no claimed-hung entry; tick age 30m > 2x cadence(5m); < 2x stall.
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}],
                     last_tick_wall=self.NOW - 1800, next_tick_minutes=5)
        self.assertTrue(self._health(rd).startswith("STALE-TICK"))

    def test_running(self):
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}],
                     last_tick_wall=self.NOW - 30, next_tick_minutes=10)
        self.assertEqual(self._health(rd), "RUNNING")

    def test_list_runs_carries_health(self):
        root = Path(tempfile.mkdtemp())
        rd = _mk_run([{"name": "run-01", "state": "completed"}], done=True)
        # move the run under the shared root
        dst = root / "r1"; dst.mkdir()
        (dst / "harness_status.json").write_text(
            (rd / "harness_status.json").read_text())
        rows = DATA.list_runs(root, now=self.NOW)
        self.assertEqual(rows[0]["health"], "DONE")
        self.assertIn("DONE", DATA.format_picker_row(rows[0]))


def _snapshot(rd):
    out = {}
    for p in sorted(Path(rd).rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(rd))] = (st.st_mtime_ns, st.st_size,
                                           hash(p.read_bytes()))
    return out


class ReadOnlyBoundary(unittest.TestCase):                     # PIN

    def test_views_never_write_only_kill_does(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "IN_PROGRESS"},
                      {"name": "run-02", "state": "queued", "hb": False}])
        before = _snapshot(rd)
        # exercise every READ view several times
        for _ in range(3):
            DATA.list_runs(rd.parent)
            DATA.run_health(rd)
            DATA.run_view_frame(rd, interval=2.0, now=2000.0)
            for name in DATA.entry_names(rd):
                DATA.entry_detail(rd, name)
                DATA.heartbeat_history(rd, name)
            DATA.journal_tail(rd)
        self.assertEqual(before, _snapshot(rd), "a read view mutated the run-dir")
        for ctrl in ("STOP", "PAUSE", "RESUME", "CANCEL", "POOL", "CADENCE",
                     "POLL-NOW", ".tick.lock"):
            self.assertFalse((rd / ctrl).exists(),
                             "a read view created %s" % ctrl)

    def test_kill_cancel_writes_only_control_file(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed",
                       "hb_status": "IN_PROGRESS"}])
        before = set(str(p.relative_to(rd)) for p in rd.rglob("*"))
        p = DATA.write_kill_control(rd, run_name="run-01", verb="CANCEL")
        self.assertEqual(p, rd / "CANCEL")
        self.assertEqual(p.read_text(encoding="utf-8"), "run-01")  # value channel
        after = set(str(q.relative_to(rd)) for q in rd.rglob("*"))
        self.assertEqual(after - before, {"CANCEL"},
                         "CANCEL wrote more than the one control file")

    def test_kill_stop_writes_only_stop(self):
        rd = _mk_run([{"name": "run-01", "state": "running",
                       "hb_status": "IN_PROGRESS"}])
        before = set(str(p.relative_to(rd)) for p in rd.rglob("*"))
        p = DATA.write_kill_control(rd, verb="STOP")
        self.assertEqual(p, rd / "STOP")
        after = set(str(q.relative_to(rd)) for q in rd.rglob("*"))
        self.assertEqual(after - before, {"STOP"})

    def test_kill_cancel_requires_run_id(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed"}])
        with self.assertRaises(ValueError):
            DATA.write_kill_control(rd, verb="CANCEL")     # no run id
        self.assertFalse((rd / "CANCEL").exists())          # nothing written

    def test_kill_rejects_unknown_verb(self):
        rd = _mk_run([{"name": "run-01", "state": "claimed"}])
        with self.assertRaises(ValueError):
            DATA.write_kill_control(rd, run_name="run-01", verb="NUKE")


class Clipboard(unittest.TestCase):

    def test_copy_invokes_platform_tool(self):
        calls = {}

        class _Proc:
            returncode = 0

        def fake_run(cmd, input=None, capture_output=None):
            calls["cmd"] = cmd
            calls["input"] = input
            return _Proc()

        orig_which = DATA.shutil.which
        DATA.shutil.which = lambda exe: "/usr/bin/" + exe   # pretend all present
        try:
            ok, info = DATA.copy_to_clipboard("hello world", _run=fake_run)
        finally:
            DATA.shutil.which = orig_which
        self.assertTrue(ok)
        self.assertEqual(calls["input"], b"hello world")
        self.assertTrue(calls["cmd"][0].startswith("/usr/bin/"))

    def test_copy_degrades_when_no_tool(self):
        orig_which = DATA.shutil.which
        DATA.shutil.which = lambda exe: None               # nothing installed
        try:
            ok, info = DATA.copy_to_clipboard("x", _run=lambda *a, **k: None)
        finally:
            DATA.shutil.which = orig_which
        self.assertFalse(ok)
        self.assertIn("no clipboard tool", info)

    def test_copy_handles_tool_failure(self):
        class _Bad:
            returncode = 1
        orig_which = DATA.shutil.which
        DATA.shutil.which = lambda exe: "/usr/bin/" + exe
        try:
            ok, _info = DATA.copy_to_clipboard("x", _run=lambda *a, **k: _Bad())
        finally:
            DATA.shutil.which = orig_which
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
