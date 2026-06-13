"""FR-40 wrap-and-run adapter `heartbeat.py wrap` (instr 025, Iteration 7).

`wrap` launches a command as its OWN CHILD, captures stdout+stderr to a file it
tails, emits STARTING then TIMER-DRIVEN IN_PROGRESS keepalives, and the terminal
COMPLETED/FAILED straight from the child's EXIT CODE. Two load-bearing claims,
tested separately:
  * doneness is exit-code-only (0 -> COMPLETED, nonzero -> FAILED);
  * keepalives are TIMER-driven, not output-driven -- a SILENT child still
    keepalives on cadence, so a quiet job never false-STALLs.
The keepalive cadence is tested through the injected clock seam (explicit epoch
values into _Keepalive.maybe_emit) -- NO real sleeps, so it's deterministic.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 025:
  Pin 1: test_exit_zero_maps_completed / test_nonzero_maps_failed.
    Mutation: in _cmd_wrap, flip `terminal = "COMPLETED" if rc == 0 else
      "FAILED"` to `rc != 0`.
    Observed: an exit-0 child is reported FAILED -> the test FAILs. Restored OK.
  Pin 2: test_silent_child_still_keepalives.
    Mutation: in _Keepalive.maybe_emit, early-return unless the capture file has
      output (make it output-driven).
    Observed: a silent child emits no keepalive -> the test FAILs (it would
      false-STALL in production). Restored OK.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
import io
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_hb():
    spec = importlib.util.spec_from_file_location("hb_fr40", _ROOT / "bin" / "heartbeat.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HB = _load_hb()


def _lines(hb_path):
    return [json.loads(l) for l in Path(hb_path).read_text().splitlines() if l.strip()]


def _statuses(hb_path):
    return [o["status"] for o in _lines(hb_path)]


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class ExitMappingTests(_Base):
    """Doneness = exit code only (fast child stubs, no clock dependency)."""

    def _wrap(self, py):
        hb = self.tmp / "hb.ndjson"
        rc = HB.main(["wrap", "--task-id", "t", "--heartbeat-path", str(hb),
                      "--", sys.executable, "-c", py])
        return rc, hb

    def test_exit_zero_maps_completed(self):
        rc, hb = self._wrap("import sys; sys.exit(0)")
        st = _statuses(hb)
        self.assertEqual(st[0], "STARTING")
        self.assertEqual(st[-1], "COMPLETED")
        self.assertEqual(rc, 0)

    def test_nonzero_maps_failed(self):
        rc, hb = self._wrap("import sys; sys.exit(7)")
        self.assertEqual(_statuses(hb)[-1], "FAILED")
        self.assertEqual(rc, 1)              # adapter mirrors the child's status

    def test_doneness_ignores_output_text(self):
        # A child that PRINTS "FAILED" but exits 0 is COMPLETED (never parsed).
        rc, hb = self._wrap("print('ERROR FAILED everything is broken'); "
                            "import sys; sys.exit(0)")
        self.assertEqual(_statuses(hb)[-1], "COMPLETED")

    def test_terminal_record_carries_capture_as_result_file(self):
        rc, hb = self._wrap("print('hi'); import sys; sys.exit(0)")
        term = _lines(hb)[-1]
        self.assertTrue(term["result_file"].endswith("wrap.out"))
        self.assertEqual(Path(term["result_file"]).read_text().strip(), "hi")

    def test_unlaunchable_command_is_failed(self):
        hb = self.tmp / "hb.ndjson"
        rc = HB.main(["wrap", "--task-id", "t", "--heartbeat-path", str(hb),
                      "--", str(self.tmp / "does-not-exist-cmd")])
        self.assertEqual(_statuses(hb)[-1], "FAILED")


class KeepaliveSchedulerTests(_Base):
    """Timer-driven cadence via the injected clock -- NO real sleeps."""

    def test_interval_is_min_grace_and_third_stall(self):
        self.assertEqual(HB.keepalive_interval_secs(600, 2700), 600.0)   # min(600, 900)
        self.assertEqual(HB.keepalive_interval_secs(1200, 2700), 900.0)  # min(1200, 900)
        self.assertEqual(HB.keepalive_interval_secs(0, 0), 1.0)          # floor

    def _ka(self, interval=600.0, start=1000.0):
        hb = self.tmp / "hb.ndjson"
        cap = self.tmp / "cap.out"
        cap.write_text("")                   # exists but EMPTY (silent so far)
        ka = HB._Keepalive(hb_path=hb, task_id="t", capture_path=cap,
                           interval_secs=interval, start_ts=start)
        return ka, hb, cap

    def test_keepalive_fires_on_cadence(self):
        ka, hb, _ = self._ka(interval=600.0, start=1000.0)
        self.assertFalse(ka.maybe_emit(1000 + 300))   # before the floor: silent
        self.assertTrue(ka.maybe_emit(1000 + 600))    # at the floor: fires
        self.assertFalse(ka.maybe_emit(1000 + 900))   # < interval since last
        self.assertTrue(ka.maybe_emit(1000 + 1200))   # next interval: fires
        self.assertEqual(_statuses(hb), ["IN_PROGRESS", "IN_PROGRESS"])
        # the heartbeat ts reflects the INJECTED clock, not wall time
        self.assertEqual(_lines(hb)[0]["ts"], HB._iso_from_epoch(1600.0))

    def test_silent_child_still_keepalives(self):
        # THE false-STALL guard: the capture file stays EMPTY (no output) yet
        # keepalives MUST keep firing on cadence (timer-driven, not output-driven).
        ka, hb, cap = self._ka(interval=100.0, start=0.0)
        fired = [ka.maybe_emit(t) for t in (100.0, 200.0, 300.0)]
        self.assertEqual(fired, [True, True, True])
        self.assertEqual(ka.count, 3)
        for o in _lines(hb):
            self.assertEqual(o["status"], "IN_PROGRESS")
            self.assertIn("running", o["label"])      # neutral fallback label
        self.assertEqual(cap.read_text(), "")          # genuinely no output

    def test_label_is_most_recent_output_line(self):
        ka, hb, cap = self._ka(interval=100.0, start=0.0)
        cap.write_text("first line\nsecond line\n")
        self.assertTrue(ka.maybe_emit(100.0))
        self.assertEqual(_lines(hb)[-1]["label"], "second line")
        cap.write_text("first line\nsecond line\nthird now\n")
        self.assertTrue(ka.maybe_emit(200.0))
        self.assertEqual(_lines(hb)[-1]["label"], "third now")


def _load_tick():
    spec = importlib.util.spec_from_file_location("tick_fr40", _ROOT / "bin" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TICK = _load_tick()


class EngineDonenessFromStatusFieldTests(_Base):
    """Regression for a Council finding: the engine must detect a terminal by
    the heartbeat STATUS FIELD, never by substring-scanning the line -- else a
    wrapped command whose label/output contains 'FAILED'/'COMPLETED' is
    mis-reaped, defeating FR-40's exit-code-only doneness."""

    def _hb(self, *objs):
        hb = self.tmp / "hb.ndjson"
        hb.write_text("\n".join(json.dumps(o) for o in objs) + "\n")
        return hb

    def test_label_keyword_is_not_a_terminal(self):
        hb = self._hb(
            {"status": "STARTING", "label": "wrap: run the build that FAILED before"},
            {"status": "IN_PROGRESS", "label": "test_foo COMPLETED ok, 0 ABANDONED"})
        self.assertIsNone(TICK._terminal_status_of(hb))   # no status field is terminal

    def test_status_field_terminal_is_detected(self):
        hb = self._hb(
            {"status": "IN_PROGRESS", "label": "still working"},
            {"status": "COMPLETED", "result_file": "/x", "summary": "done"})
        self.assertEqual(TICK._terminal_status_of(hb), "COMPLETED")

    def test_malformed_and_nonstatus_lines_skipped(self):
        hb = self.tmp / "hb.ndjson"
        hb.write_text('not json at all FAILED\n'
                      + json.dumps({"label": "no status field, mentions COMPLETED"}) + "\n")
        self.assertIsNone(TICK._terminal_status_of(hb))


if __name__ == "__main__":
    unittest.main()
