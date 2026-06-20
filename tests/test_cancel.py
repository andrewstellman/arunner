"""FR-39 CANCEL (instr 023, Iteration 5).

CANCEL <run-NN> is a one-shot, value-carrying control (run id in the file
body). It marks a named run `abandoned` (terminal) via the SAME synthesis path
the genuine FAILED reap uses (`_synthesize_failure`), so the cancelled run
stays auditable in results/ and frees its pool slot (it leaves
_INFLIGHT_STATES). It NEVER un-terminals a finished run, never kills the worker
(the detached orphan, if any, runs to its own terminal -- so the true
running-process count may briefly exceed pool_size by design), and is a
consumed no-op (warned) on a terminal/unknown/unparseable target.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 023:
  Pin: test_cancel_of_completed_is_noop_byte_identical.
    Mutation: in _ctl_cancel, remove the
      `elif runs[run_id]["state"] in _TERMINAL_STATES:` no-op guard (so CANCEL
      of a completed run falls through to the abandon branch).
    Observed: run-01's state flips completed -> abandoned (un-terminaling a
      genuine completion; its COMPLETED results record now disagrees with the
      state) -> the test FAILs (expects state still 'completed'). Restored -> OK.
"""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_tick():
    spec = importlib.util.spec_from_file_location("tick_fr39", _ROOT / "arunner" / "engine" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load_tick()


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._n = 0

    def tearDown(self):
        os.environ.pop("ARUNNER_RUNS_DIR", None)
        self._tmp.cleanup()

    def _fresh(self, n=2, pool=1):
        self._n += 1
        os.environ["ARUNNER_RUNS_DIR"] = str(self.tmp / ("runs%d" % self._n))
        entries = [{"id": "t%d" % i, "repo": "/tmp",
                    "mode": "agent", "prompt": "x"}
                   for i in range(n)]
        pf = self.tmp / ("plan%d.json" % self._n)
        pf.write_text(json.dumps({"pool_size": pool, "jobs": entries}))
        return Path(T.init_run(pf))

    def _status(self, rd):
        return json.loads((rd / "harness_status.json").read_text())

    def _set_state(self, rd, run, state):
        st = self._status(rd)
        st["runs"][run]["state"] = state
        st["counts"] = T._recount(st["runs"])
        (rd / "harness_status.json").write_text(json.dumps(st))

    def _write_result(self, rd, job_id="job-00001", terminal="COMPLETED"):
        rp = rd / "results" / (job_id.replace("job-", "result-") + ".json")
        rp.write_text(json.dumps({
            "job_id": job_id, "task_id": "t0", "terminal_status": terminal,
            "result_file": "/tmp/real-summary.md", "summary": "genuine completion",
            "reaped_ts": "2026-01-01T00:00:00Z", "synthesized": False}, indent=2))
        return rp


class CancelTests(_Base):

    def test_cancel_running_abandons_with_record_and_frees_slot(self):
        rd = self._fresh(n=2, pool=1)
        self._set_state(rd, "run-01", "running")          # in-flight, holds the only slot
        (rd / "CANCEL").write_text("run-01")
        out = T.tick(rd)
        st = self._status(rd)
        self.assertEqual(st["runs"]["run-01"]["state"], "abandoned")   # terminal
        rp = rd / "results" / "result-00001.json"
        self.assertTrue(rp.exists())                                   # synthesized record
        rec = json.loads(rp.read_text())
        self.assertEqual(rec["terminal_status"], "ABANDONED")
        self.assertTrue(rec["synthesized"])
        self.assertFalse((rd / "CANCEL").exists())                     # one-shot consumed
        # the freed slot back-fills the queued run THIS tick
        self.assertEqual(st["runs"]["run-02"]["state"], "claimed")
        self.assertTrue(any(d.get("run") == "run-02" for d in out["dispatch_list"]))

    def test_cancel_of_completed_is_noop_byte_identical(self):
        rd = self._fresh(n=1, pool=1)
        self._set_state(rd, "run-01", "completed")
        rp = self._write_result(rd, "job-00001", "COMPLETED")
        before = rp.read_bytes()
        (rd / "CANCEL").write_text("run-01")
        T.tick(rd)
        st = self._status(rd)
        self.assertEqual(st["runs"]["run-01"]["state"], "completed")   # NOT un-terminaled
        self.assertEqual(rp.read_bytes(), before)                      # record byte-identical
        self.assertFalse((rd / "CANCEL").exists())                     # consumed (no-op)

    def test_cancel_idempotent_second_cancel_of_abandoned(self):
        rd = self._fresh(n=1, pool=1)
        self._set_state(rd, "run-01", "running")
        (rd / "CANCEL").write_text("run-01")
        T.tick(rd)                                                     # 1st: abandons
        rp = rd / "results" / "result-00001.json"
        self.assertEqual(self._status(rd)["runs"]["run-01"]["state"], "abandoned")
        before = rp.read_bytes()
        (rd / "CANCEL").write_text("run-01")
        T.tick(rd)                                                     # 2nd: no-op
        self.assertEqual(self._status(rd)["runs"]["run-01"]["state"], "abandoned")
        self.assertEqual(rp.read_bytes(), before)                      # record unchanged
        self.assertFalse((rd / "CANCEL").exists())

    def test_cancel_unknown_and_unparseable_are_warned_noops(self):
        rd = self._fresh(n=1, pool=1)
        self._set_state(rd, "run-01", "running")
        for raw, kind in (("run-99", "unknown"), ("not-a-run", "unparseable"),
                          ("", "unparseable")):
            (rd / "CANCEL").write_text(raw)
            status = self._status(rd)
            warnings = T._apply_controls(rd, status)
            self.assertEqual(status["runs"]["run-01"]["state"], "running",
                             "CANCEL %r must not touch other runs" % raw)
            self.assertTrue(any("CANCEL" in w for w in warnings), "no warn for %r" % raw)
            self.assertIn(kind, " ".join(warnings))
            self.assertFalse((rd / "CANCEL").exists(), "%r should be consumed" % raw)

    def test_cancel_run_id_accepts_padded_and_bare(self):
        # value channel parses run-02 / run-2 / 2 to the canonical run-02
        for raw in ("run-02", "run-2", "2"):
            self.assertEqual(T._parse_run_id(raw), "run-02")
        for bad in ("", "abc", "run-", "run-2x", None):
            self.assertIsNone(T._parse_run_id(bad))


if __name__ == "__main__":
    unittest.main()
