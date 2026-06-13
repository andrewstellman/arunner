"""FR-42 plan pre-flight `tick.py --check` (instr 024, Iteration 6).

A hand-rolled, stdlib-only validator (NFR-3 forbids a jsonschema dependency)
that reports ALL problems at once so an adopter fixes config proactively rather
than as a reactive AUTH_OR_LAUNCH_FAILED after launch spend. The placeholder
checks REUSE the engine's _PLACEHOLDERS / _SHELL_PLACEHOLDERS tuples so the
check can never drift from what _dispatch actually substitutes.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 024:
  Pin: test_subagent_requires_each_engine_placeholder.
    Mutation: in _check_entry, skip the subagent placeholder loop (e.g.
      `for ph in ():`) so missing placeholders are not reported.
    Observed: a prompt missing {RUN_DIR} no longer produces a problem -> the
      test FAILs. Restored -> OK.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_tick():
    spec = importlib.util.spec_from_file_location("tick_fr42", _ROOT / "bin" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load_tick()

# a worker_prompt carrying the full engine placeholder block (valid subagent)
_FULL_PROMPT = "".join("{%s}" % ph for ph in T._PLACEHOLDERS)


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)       # an existing dir for target_repo
        self._n = 0

    def tearDown(self):
        self._tmp.cleanup()

    def _plan_file(self, plan):
        self._n += 1
        p = self.tmp / ("plan%d.json" % self._n)
        p.write_text(json.dumps(plan))
        return p

    def _good_subagent(self):
        return {"task_id": "t", "target_repo": str(self.tmp),
                "dispatch_mode": "subagent", "worker_prompt": _FULL_PROMPT}

    def _check(self, plan):
        return T.check_plan(self._plan_file(plan))


class CheckPlanTests(_Base):

    def test_valid_plan_passes_clean(self):
        plan = {"schema_version": "1", "pool_size": 2,
                "entries": [self._good_subagent()]}
        self.assertEqual(self._check(plan), [])

    def test_missing_required_key(self):
        e = self._good_subagent(); del e["task_id"]
        probs = self._check({"entries": [e]})
        self.assertTrue(any("task_id" in p for p in probs))

    def test_bad_dispatch_mode_enum(self):
        e = self._good_subagent(); e["dispatch_mode"] = "rocket"
        probs = self._check({"entries": [e]})
        self.assertTrue(any("dispatch_mode" in p and "rocket" in p for p in probs))

    def test_missing_placeholder(self):
        e = self._good_subagent()
        e["worker_prompt"] = _FULL_PROMPT.replace("{RUN_DIR}", "")
        probs = self._check({"entries": [e]})
        self.assertTrue(any("missing placeholder {RUN_DIR}" in p for p in probs))

    def test_nonexistent_target_repo(self):
        e = self._good_subagent(); e["target_repo"] = "/no/such/dir/xyz"
        probs = self._check({"entries": [e]})
        self.assertTrue(any("target_repo" in p and "existing directory" in p for p in probs))

    def test_bad_toplevel_int(self):
        probs = self._check({"pool_size": 0, "entries": [self._good_subagent()]})
        self.assertTrue(any("pool_size" in p for p in probs))

    def test_all_problems_reported_at_once(self):
        # three DISTINCT problem classes in one plan -> all three reported.
        e = self._good_subagent()
        e["dispatch_mode"] = "rocket"                       # (1) bad enum
        e["target_repo"] = "/no/such/dir"                   # (2) bad target_repo
        e["worker_prompt"] = "{HEARTBEAT_PATH}{TASK_ID}{RUN_DIR}{TARGET_REPO}"  # (3) missing {HARNESS_BIN}
        probs = self._check({"entries": [e]})
        self.assertTrue(any("dispatch_mode" in p for p in probs), probs)
        self.assertTrue(any("target_repo" in p for p in probs), probs)
        # NOTE: missing-placeholder only checked for subagent; this entry's mode
        # is invalid so it's not subagent -> use a separate accumulation case:
        plan = {"pool_size": 0, "entries": [
            {"task_id": "", "target_repo": "/no/such", "dispatch_mode": "subagent",
             "worker_prompt": "{HEARTBEAT_PATH}"}]}   # missing task_id, bad repo, 4 missing placeholders, bad pool
        probs2 = self._check(plan)
        classes = {
            "pool": any("pool_size" in p for p in probs2),
            "task_id": any("task_id" in p for p in probs2),
            "placeholder": any("missing placeholder" in p for p in probs2),
            "target_repo": any("existing directory" in p for p in probs2),
        }
        self.assertTrue(all(classes.values()), "%s -> %s" % (classes, probs2))
        self.assertGreaterEqual(len(probs2), 4)

    def test_subagent_requires_each_engine_placeholder(self):
        # reuse-proof: dropping ANY one of _PLACEHOLDERS is flagged for THAT one.
        for ph in T._PLACEHOLDERS:
            e = self._good_subagent()
            e["worker_prompt"] = _FULL_PROMPT.replace("{%s}" % ph, "")
            probs = self._check({"entries": [e]})
            self.assertTrue(any(("missing placeholder {%s}" % ph) in p for p in probs),
                            "dropping {%s} was not flagged" % ph)

    def test_shell_heartbeat_route(self):
        base = {"task_id": "t", "target_repo": str(self.tmp), "dispatch_mode": "shell"}
        # no heartbeat route -> problem
        no_route = dict(base, worker_prompt="x", worker_cmd=["echo", "hi"])
        self.assertTrue(any("HEARTBEAT_PATH" in p for p in self._check({"entries": [no_route]})))
        # via worker_cmd -> clean
        via_cmd = dict(base, worker_prompt="x",
                       worker_cmd=["w", "--hb", "{HEARTBEAT_PATH}"])
        self.assertEqual(self._check({"entries": [via_cmd]}), [])
        # via {PROMPT_FILE} + prompt carrying the placeholder -> clean
        via_prompt = dict(base, worker_prompt="HB={HEARTBEAT_PATH}",
                          worker_cmd=["w", "--prompt", "{PROMPT_FILE}"])
        self.assertEqual(self._check({"entries": [via_prompt]}), [])

    def test_shell_requires_worker_cmd(self):
        e = {"task_id": "t", "target_repo": str(self.tmp), "dispatch_mode": "shell",
             "worker_prompt": "{HEARTBEAT_PATH}"}
        self.assertTrue(any("worker_cmd" in p for p in self._check({"entries": [e]})))

    def test_unknown_placeholder_typo_flagged(self):
        e = self._good_subagent()
        e["worker_prompt"] = _FULL_PROMPT + "{RUN_DOR}"     # typo
        probs = self._check({"entries": [e]})
        self.assertTrue(any("unknown placeholder {RUN_DOR}" in p for p in probs))

    def test_missing_entries(self):
        self.assertTrue(any("entries" in p for p in self._check({"pool_size": 1})))

    def test_bad_json_and_missing_file(self):
        bad = self.tmp / "bad.json"; bad.write_text("{not json")
        self.assertTrue(any("JSON" in p for p in T.check_plan(bad)))
        self.assertTrue(any("cannot read" in p for p in T.check_plan(self.tmp / "nope.json")))

    def test_exit_codes_and_report_via_main(self):
        good = self._plan_file({"entries": [self._good_subagent()]})
        bad = self._plan_file({"entries": [dict(self._good_subagent(),
                                                dispatch_mode="rocket")]})
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc_good = T.main(["tick.py", "--check", str(good)])
            rc_bad = T.main(["tick.py", "--check", str(bad)])
        self.assertEqual(rc_good, 0)
        self.assertEqual(rc_bad, 1)
        report = out.getvalue()
        self.assertIn("plan OK", report)
        self.assertIn("plan FAILED", report)

    def test_stdlib_only_no_jsonschema(self):
        # NFR-3: the engine must not IMPORT jsonschema (the word may appear in
        # comments referencing the constraint -- check for an actual import).
        src = (_ROOT / "bin" / "tick.py").read_text()
        self.assertNotIn("import jsonschema", src)
        self.assertNotIn("from jsonschema", src)


if __name__ == "__main__":
    unittest.main()
