"""instr 018 — the injectable clock seam exists on BOTH time surfaces.

The deterministic core is unit-testable because time is injectable, not read
from the wall clock. The tick engine already honors ``ARUNNER_NOW`` (epoch
float) for stall / wall-clock-jump logic (FR-8); instruction 018 adds the
mirror to the heartbeat surface so the future wrap-adapter keepalive cadence
(Iteration 7) and in-context timing (Iteration 12) are red/green-able without
``sleep``-based flakiness. This pins that both surfaces read through the seam.
"""
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ClockSeamTests(unittest.TestCase):

    def setUp(self):
        self._saved = os.environ.get("ARUNNER_NOW")
        os.environ["ARUNNER_NOW"] = "1000000000"  # 2001-09-09T01:46:40Z

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("ARUNNER_NOW", None)
        else:
            os.environ["ARUNNER_NOW"] = self._saved

    def test_engine_now_honors_seam(self):
        tk = _load("tk_seam", "bin/tick.py")
        self.assertEqual(tk._now(), 1000000000.0)

    def test_heartbeat_utc_iso_honors_seam(self):
        hb = _load("hb_seam", "bin/heartbeat.py")
        self.assertEqual(hb._utc_iso(), "2001-09-09T01:46:40Z")

    def test_heartbeat_falls_back_when_unset(self):
        os.environ.pop("ARUNNER_NOW", None)
        hb = _load("hb_seam2", "bin/heartbeat.py")
        # real now -- just assert it's a well-formed Zulu stamp, not the frozen one
        ts = hb._utc_iso()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertNotEqual(ts, "2001-09-09T01:46:40Z")


if __name__ == "__main__":
    unittest.main()
