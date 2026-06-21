"""FR-61 — prompt-from-file + light {var} templating (instr 002).

An entry/step MAY source its prompt from a Markdown file (worker_prompt_file)
instead of an inline worker_prompt (exactly one; both = --check error). The file
is resolved relative to the PLAN file's directory and SNAPSHOTTED into the
run-dir at --init (mutating the source afterward never changes the run). A flat
`vars` map substitutes designated {key}s by literal str.replace BEFORE the
engine's reserved placeholders, and does NOT scan for stray braces -- so a
prompt carrying literal single-brace JSON survives unmangled.

MUTATION-VERIFY EVIDENCE (instr 002):
  Pin: test_literal_single_brace_json_survives (Council FIX-2).
    Mutation: make _apply_vars scan-and-reject stray {name} tokens (e.g. raise
      on any leftover "{...}"). Observed: the literal JSON block trips the error
      and the test FAILs. Restored (designated-key replace only) -> OK.
  Pin: test_snapshot_is_authoritative.
    Mutation: in _snapshot_prompt, keep worker_prompt_file and re-read it at
      dispatch instead of snapshotting. Observed: mutating the source changes
      the dispatched prompt and the test FAILs. Restored -> OK.
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
    spec = importlib.util.spec_from_file_location(
        "tick_fr61", _ROOT / "arunner" / "engine" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load_tick()
_PH = "".join("{%s}" % p for p in T._PLACEHOLDERS)   # the 5 reserved placeholders


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        os.environ["ARUNNER_RUNS_DIR"] = str(self.tmp / "harness_runs")
        os.environ.pop("ARUNNER_NOW", None)

    def tearDown(self):
        os.environ.pop("ARUNNER_RUNS_DIR", None)
        self._tmp.cleanup()

    def _plan_file(self, plan, name="plan.json"):
        pf = self.tmp / name
        pf.write_text(json.dumps(plan))
        return pf

    def _init(self, plan):
        return Path(T.init_run(self._plan_file(plan)))

    def _dispatched_prompt(self, plan):
        rd = self._init(plan)
        out = T.tick(rd)
        subs = [d for d in out["dispatch_list"] if d.get("dispatch_mode") == "subagent"]
        self.assertTrue(subs, "no subagent dispatch emitted")
        return subs[0]["worker_prompt"], rd


def _file_entry(tid, wpf, repo, **extra):
    e = {"id": tid, "repo": repo, "mode": "agent", "prompt_file": wpf}
    e.update(extra)
    return e


class DispatchTests(_Base):
    def test_file_prompt_dispatches_byte_for_byte(self):
        body = "WORK\n" + _PH + "\nEND"
        (self.tmp / "p.md").write_text(body)
        prompt, rd = self._dispatched_prompt(
            {"jobs": [_file_entry("t1", "p.md", str(self.tmp))]})
        # the reserved placeholders are resolved; the rest is byte-identical
        expect = body.replace("{HEARTBEAT_PATH}", str(rd / "run-01" / "heartbeat.ndjson")) \
                     .replace("{TASK_ID}", "t1") \
                     .replace("{RUN_DIR}", str(rd / "run-01")) \
                     .replace("{TARGET_REPO}", str(self.tmp)) \
                     .replace("{HARNESS_BIN}", T._HARNESS_BIN)
        self.assertEqual(prompt, expect)

    def test_plan_dir_relative_resolution_from_other_cwd(self):
        sub = self.tmp / "prompts"
        sub.mkdir()
        (sub / "p.md").write_text("REL " + _PH)
        cwd = os.getcwd()
        other = tempfile.TemporaryDirectory()
        try:
            os.chdir(other.name)        # NOT the plan dir -- proves plan-relative
            prompt, _ = self._dispatched_prompt(
                {"jobs": [_file_entry("t1", "prompts/p.md", str(self.tmp))]})
        finally:
            os.chdir(cwd)
            other.cleanup()
        self.assertIn("REL ", prompt)
        self.assertIn("{", "{")            # sanity
        self.assertNotIn("{RUN_DIR}", prompt)

    def test_snapshot_is_authoritative(self):
        src = self.tmp / "p.md"
        src.write_text("ORIGINAL " + _PH)
        rd = self._init({"jobs": [_file_entry("t1", "p.md", str(self.tmp))]})
        # snapshot artifact exists in the run-dir (NFR-9 self-sufficiency)
        self.assertTrue((rd / "run-01" / "prompt.snapshot.md").is_file())
        src.write_text("MUTATED " + _PH)   # change the source AFTER --init
        out = T.tick(rd)
        prompt = out["dispatch_list"][0]["worker_prompt"]
        self.assertIn("ORIGINAL", prompt)
        self.assertNotIn("MUTATED", prompt)

    def test_skill_fallback_guide_var_round_trips(self):
        (self.tmp / "p.md").write_text("Guide: {skill_fallback_guide}\n" + _PH)
        prompt, _ = self._dispatched_prompt(
            {"jobs": [_file_entry("t1", "p.md", str(self.tmp),
                                     vars={"skill_fallback_guide": "USE-THE-GUIDE"})]})
        self.assertIn("Guide: USE-THE-GUIDE", prompt)
        self.assertNotIn("{skill_fallback_guide}", prompt)

    def test_literal_single_brace_json_survives(self):
        # Council FIX-2: a literal single-brace JSON block must survive the {var}
        # pass unmangled AND must NOT trip an unresolved-{name} error at --check.
        json_block = '{"phase": 3, "skip": false, "note": "literal"}'
        (self.tmp / "p.md").write_text(
            "Guide: {skill_fallback_guide}\nJSON: " + json_block + "\n" + _PH)
        plan = {"jobs": [_file_entry("t1", "p.md", str(self.tmp),
                                        vars={"skill_fallback_guide": "G"})]}
        # --check is clean (the JSON braces are not placeholder-shaped)
        self.assertEqual(T.check_plan(self._plan_file(plan, "checkplan.json")), [])
        prompt, _ = self._dispatched_prompt(plan)
        self.assertIn(json_block, prompt)            # byte-identical, unmangled
        self.assertIn("Guide: G", prompt)            # the declared var substituted

    def test_inline_prompt_unchanged_regression(self):
        e = {"id": "t1", "repo": str(self.tmp),
             "mode": "agent", "prompt": "INLINE " + _PH}
        prompt, _ = self._dispatched_prompt({"jobs": [e]})
        self.assertIn("INLINE", prompt)


class CheckTests(_Base):
    def _check(self, plan):
        return T.check_plan(self._plan_file(plan, "chk.json"))

    def test_both_prompt_sources_is_error(self):
        # agent mode: exactly one of prompt / prompt_file (both = --check error)
        e = {"id": "t1", "repo": str(self.tmp), "mode": "agent",
             "prompt": _PH, "prompt_file": "p.md"}
        (self.tmp / "p.md").write_text(_PH)
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("exactly one of prompt / prompt_file" in p
                            for p in probs), probs)

    def test_no_prompt_source_is_error(self):
        # Re-aimed: an agent job with neither prompt nor prompt_file is rejected
        # (preserves the "must declare a prompt source" intent).
        e = {"id": "t1", "repo": str(self.tmp), "mode": "agent"}
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("agent mode needs a prompt or prompt_file" in p
                            for p in probs), probs)

    def test_vars_reserved_key_is_error(self):
        (self.tmp / "p.md").write_text(_PH)
        e = _file_entry("t1", "p.md", str(self.tmp), vars={"TASK_ID": "x"})
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("vars" in p and "reserved" in p for p in probs), probs)

    def test_vars_value_reserved_token_is_error(self):
        (self.tmp / "p.md").write_text(_PH)
        e = _file_entry("t1", "p.md", str(self.tmp),
                        vars={"foo": "leak {HEARTBEAT_PATH}"})
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("vars" in p and "reserved" in p for p in probs), probs)

    def test_missing_prompt_file_is_error(self):
        e = _file_entry("t1", "nope.md", str(self.tmp))
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("cannot read" in p for p in probs), probs)

    def test_file_prompt_missing_placeholder_is_clean(self):
        # Re-aimed (behavior change): agent prompts are now BARE -- the engine
        # auto-injects the placeholder preamble at dispatch, so a file with NO
        # reserved placeholders is no longer a --check error (it is clean).
        (self.tmp / "p.md").write_text("no placeholders here")
        e = _file_entry("t1", "p.md", str(self.tmp))
        self.assertEqual(self._check({"jobs": [e]}), [])

    def test_file_prompt_unknown_placeholder_flagged(self):
        # Re-aimed companion: the placeholder check now rejects an unknown
        # {TYPO} token the author wrote (vs. the old "missing placeholder").
        (self.tmp / "p.md").write_text("oops {HEARTBEATPATH}\n" + _PH)
        e = _file_entry("t1", "p.md", str(self.tmp))
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("unknown placeholder" in p for p in probs), probs)

    def test_plan_level_vars_validated(self):
        (self.tmp / "p.md").write_text(_PH)
        plan = {"vars": {"RUN_DIR": "x"},
                "jobs": [_file_entry("t1", "p.md", str(self.tmp))]}
        probs = self._check(plan)
        self.assertTrue(any("plan.vars" in p and "reserved" in p for p in probs), probs)


if __name__ == "__main__":
    unittest.main()
