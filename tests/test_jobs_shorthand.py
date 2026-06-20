"""FR-43 jobs.py (defaults + placeholder filler) + the examples/ anti-drift
binding, for the ONE mode-discriminated format (instr 004 format collapse).

There is no longer a shorthand/canonical dialect: a plan is a single `jobs`
list. jobs.expand_jobs is now a thin, idempotent convenience layer — it merges
plan-level `defaults` under each job and injects the placeholder preamble into
each `agent` prompt (the engine does the same at --init/dispatch, so a bare
source and an expanded plan run identically). The load-bearing test is the
anti-drift binding: EVERY example in examples/ expands and --checks clean, so a
schema/expander drift fails loudly here.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 004:
  Pin: test_examples_round_trip_through_check.
    Mutation: drop a key from jobs._PLACEHOLDER_KEYS (so the injected preamble
      omits a placeholder) -- the examples still --check clean (placeholders are
      no longer REQUIRED), so instead the binding's teeth are: corrupt an
      example's `mode` -> --check rejects -> test_binding_catches_a_bad_example
      FAILs. Verified by hand: setting an example mode to "bogus" trips it.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = sorted((_ROOT / "examples").glob("*.json"))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


JOBS = _load("jobs_fr43", "arunner/engine/jobs.py")
TICK = _load("tick_fr43", "arunner/engine/tick.py")


def _check_plan_dict(plan, real_repo):
    # Examples carry illustrative repo paths; substitute a REAL dir so the
    # binding validates SCHEMA + mode conformance, not literal paths.
    for e in plan.get("jobs", []):
        if e.get("repo"):
            e["repo"] = str(real_repo)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(json.dumps(plan))
        path = fh.name
    try:
        return TICK.check_plan(path)
    finally:
        Path(path).unlink()


class ExpanderTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.real = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_defaults_merged_and_preamble_injected(self):
        doc = {"pool_size": 2, "defaults": {"repo": "/x"}, "jobs": [
            {"id": "a", "mode": "agent", "prompt": "review A"},
            {"id": "b", "mode": "command", "command": ["pytest", "-q"]},
            {"id": "c", "mode": "log", "log_path": "/x/c/log", "success_regex": "OK"}]}
        plan = JOBS.expand_jobs(doc)
        self.assertEqual(len(plan["jobs"]), 3)
        self.assertNotIn("defaults", plan)               # consumed into the jobs
        # defaults filled the repo on every job
        self.assertTrue(all(j["repo"] == "/x" for j in plan["jobs"]))
        # the agent prompt gained the placeholder preamble
        agent = plan["jobs"][0]
        for ph in ("HEARTBEAT_PATH", "TASK_ID", "RUN_DIR", "TARGET_REPO", "HARNESS_BIN"):
            self.assertIn("{%s}" % ph, agent["prompt"])
        # command/log jobs keep their mode + field
        self.assertEqual(plan["jobs"][1]["mode"], "command")
        self.assertEqual(plan["jobs"][2]["mode"], "log")
        # the WHOLE expansion passes --check
        self.assertEqual(_check_plan_dict(plan, self.real), [])

    def test_preamble_injection_is_idempotent(self):
        header = JOBS._PLACEHOLDER_HEADER
        doc = {"jobs": [{"id": "a", "repo": "/x", "mode": "agent",
                         "prompt": header + "already has it"}]}
        plan = JOBS.expand_jobs(doc)
        # not doubled
        self.assertEqual(plan["jobs"][0]["prompt"].count("HEARTBEAT_PATH={HEARTBEAT_PATH}"), 1)

    def test_doc_without_jobs_passes_through_unchanged(self):
        other = {"pool_size": 1, "something": "else"}
        self.assertEqual(JOBS.expand_jobs(other), other)

    def test_toplevel_knobs_pass_through(self):
        doc = {"pool_size": 4, "tick_interval_minutes": 9,
               "stall_threshold_minutes": 30, "jobs": [
                   {"id": "j", "repo": "/x", "mode": "agent", "prompt": "p"}]}
        plan = JOBS.expand_jobs(doc)
        self.assertEqual(plan["pool_size"], 4)
        self.assertEqual(plan["tick_interval_minutes"], 9)
        self.assertEqual(plan["stall_threshold_minutes"], 30)
        self.assertEqual(plan["jobs"][0]["id"], "j")      # ids are author-supplied


class ExamplesAntiDriftTests(unittest.TestCase):
    """The load-bearing binding: every examples/ plan expands + --checks clean."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.real = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_examples_directory_is_populated(self):
        self.assertTrue(_EXAMPLES, "no examples/*.json found")
        names = {p.name for p in _EXAMPLES}
        # the required common cases are present (one format, .json suffix)
        for required in ("agent_review.json", "shell_jobs.json", "mixed.json",
                         "wrap_vs_tail.json", "canonical_plan.json"):
            self.assertIn(required, names)

    def test_no_legacy_jobs_json_suffix(self):
        # the .jobs.json dialect suffix is gone (one format).
        self.assertFalse(any(p.name.endswith(".jobs.json") for p in _EXAMPLES))

    def test_examples_round_trip_through_check(self):
        for ex in _EXAMPLES:
            with self.subTest(example=ex.name):
                doc = json.loads(ex.read_text(encoding="utf-8"))
                plan = JOBS.expand_jobs(doc)
                problems = _check_plan_dict(plan, self.real)
                self.assertEqual(problems, [],
                                 "%s expand->check failed: %s" % (ex.name, problems))

    def test_binding_catches_a_bad_example(self):
        # prove the binding can FAIL: a job with an unknown mode is rejected.
        bad = {"jobs": [{"id": "x", "repo": "/x", "mode": "bogus", "prompt": "p"}]}
        plan = JOBS.expand_jobs(bad)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write(json.dumps(plan)); path = fh.name
        try:
            problems = TICK.check_plan(path)
        finally:
            Path(path).unlink()
        self.assertTrue(any("mode" in p and "bogus" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
