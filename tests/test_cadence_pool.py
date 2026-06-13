"""FR-37 live CADENCE + POOL overrides (instr 021, Iteration 3).

CADENCE/POOL are the first VALUE-carrying controls: the argument is read from
the control file's BODY (the value channel). They honor FR-37's two-mechanism
asymmetry:
  * CADENCE <minutes> sets a persisted tick-interval OVERRIDE that LAYERS OVER
    the per-tick plan.json re-read -- it wins over the plan value and persists
    across ticks, without editing plan.json.
  * POOL <n> WRITES BACK the sticky harness_status.json["pool_size"] (the field
    --init sets). Raising it back-fills dispatch up to the new pool on the next
    tick; lowering it below the in-flight count is honored as slots drain and
    NEVER kills a running worker (dispatch is pool-gated, reaping is not).
A non-positive / unparseable value is rejected with a warning and the prior
value retained (Postel).

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 021:
  Pin: test_cadence_override_wins_over_plan_and_persists.
    Mutation: in tick(), drop the post-control `tick_interval =
      _effective_interval(status, plan)` re-read (or make _effective_interval
      ignore the override and return the plan value).
    Observed: next_tick_minutes == 7 (the plan value) instead of 3 -> FAIL.
      Restored -> OK.
  Pin: test_pool_raise_backfills_next_tick.
    Mutation: in tick(), drop the post-control `pool_size =
      status.get("pool_size") or pool_size` re-read.
    Observed: the POOL-3 tick dispatches against the stale pool 1, so in-flight
      stays 1 instead of rising to 3 -> FAIL. Restored -> OK.
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
    spec = importlib.util.spec_from_file_location("tick_fr37", _ROOT / "bin" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load_tick()

_INFLIGHT = ("claimed", "running", "stalled")


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._n = 0

    def tearDown(self):
        os.environ.pop("WAKECYCLE_RUNS_DIR", None)
        self._tmp.cleanup()

    def _fresh(self, n=2, pool=1, tick_interval=None):
        # unique runs dir per init avoids the same-second timestamp collision
        self._n += 1
        os.environ["WAKECYCLE_RUNS_DIR"] = str(self.tmp / ("runs%d" % self._n))
        entries = [{"task_id": "t%d" % i, "target_repo": "/tmp",
                    "dispatch_mode": "subagent", "worker_prompt": "x"}
                   for i in range(n)]
        plan = {"pool_size": pool, "entries": entries}
        if tick_interval is not None:
            plan["tick_interval_minutes"] = tick_interval
        pf = self.tmp / ("plan%d.json" % self._n)
        pf.write_text(json.dumps(plan))
        return Path(T.init_run(pf))

    def _status(self, rd):
        return json.loads((rd / "harness_status.json").read_text())

    def _inflight(self, status):
        return sum(1 for r in status["runs"].values() if r["state"] in _INFLIGHT)


class CadenceTests(_Base):

    def test_cadence_override_wins_over_plan_and_persists(self):
        rd = self._fresh(n=1, pool=1, tick_interval=7)   # plan.json says 7
        (rd / "CADENCE").write_text("3")                 # value channel: file body
        out = T.tick(rd)
        # a run is in-flight after dispatch, so _next_cadence returns the raw
        # interval -- and the override (3) wins over the plan value (7).
        self.assertIn(self._status(rd)["runs"]["run-01"]["state"], _INFLIGHT)
        self.assertEqual(out["next_tick_minutes"], 3)
        st = self._status(rd)
        self.assertEqual(st["tick_interval_override"], 3)
        self.assertFalse((rd / "CADENCE").exists())       # sticky -> consumed
        # PERSISTS across a later tick with NO CADENCE file -- plan STILL says 7,
        # proving the override layers over the per-tick plan re-read.
        out2 = T.tick(rd)
        self.assertEqual(out2["next_tick_minutes"], 3)

    def test_cadence_malformed_retains_prior_and_warns(self):
        rd = self._fresh(n=1, pool=1, tick_interval=7)
        (rd / "CADENCE").write_text("5"); T.tick(rd)      # establish a prior override
        self.assertEqual(self._status(rd)["tick_interval_override"], 5)
        for bad in ("-1", "0", "abc", ""):
            (rd / "CADENCE").write_text(bad)
            status = self._status(rd)
            warnings = T._apply_controls(rd, status)
            self.assertEqual(status.get("tick_interval_override"), 5,
                             "prior cadence must survive %r" % bad)
            self.assertTrue(any("CADENCE" in w for w in warnings),
                            "no warning for %r" % bad)
            self.assertFalse((rd / "CADENCE").exists())   # rejected input consumed


class PoolTests(_Base):

    def test_pool_raise_backfills_next_tick(self):
        rd = self._fresh(n=3, pool=1)
        T.tick(rd)                                        # tick 1: only run-01 dispatches
        self.assertEqual(self._inflight(self._status(rd)), 1)
        (rd / "POOL").write_text("3")                     # value channel
        out = T.tick(rd)                                  # tick 2: POOL 3 -> back-fill
        st = self._status(rd)
        self.assertEqual(st["pool_size"], 3)              # wrote back to sticky pool_size
        self.assertEqual(self._inflight(st), 3)           # run-02 + run-03 now dispatched
        self.assertEqual(len(out["dispatch_list"]), 2)    # exactly the two back-filled
        self.assertFalse((rd / "POOL").exists())          # consumed

    def test_pool_lower_below_inflight_drains_never_kills(self):
        rd = self._fresh(n=3, pool=3)
        T.tick(rd)                                        # dispatch all 3
        self.assertEqual(self._inflight(self._status(rd)), 3)
        (rd / "POOL").write_text("1")                     # lower below in-flight
        out = T.tick(rd)
        st = self._status(rd)
        self.assertEqual(st["pool_size"], 1)              # honored
        self.assertEqual(self._inflight(st), 3)           # NONE killed -- all still in-flight
        self.assertEqual(out["dispatch_list"], [])        # and no NEW dispatch

    def test_pool_malformed_retains_prior_and_warns(self):
        rd = self._fresh(n=1, pool=2)
        for bad in ("-1", "0", "abc", ""):
            (rd / "POOL").write_text(bad)
            status = self._status(rd)
            warnings = T._apply_controls(rd, status)
            self.assertEqual(status.get("pool_size"), 2,
                             "prior pool must survive %r" % bad)
            self.assertTrue(any("POOL" in w for w in warnings),
                            "no warning for %r" % bad)
            self.assertFalse((rd / "POOL").exists())      # rejected input consumed


if __name__ == "__main__":
    unittest.main()
