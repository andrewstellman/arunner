"""FR-42 plan pre-flight `tick.py --check` for the ONE mode-discriminated format
(instr 004 format collapse; supersedes the instr-024 entries/dispatch_mode form).

A hand-rolled, stdlib-only validator (NFR-3 forbids a jsonschema dependency) that
reports ALL problems at once. It is the runtime enforcer that agrees field-for-
field with plan.schema.json: per-mode required fields + strict keys
(additionalProperties:false) + the gate `outcomes` map. The placeholder typo
check REUSES the engine's placeholder tuples so --check can never drift from
_dispatch.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 004:
  Pin: test_typo_key_rejected_per_mode (additionalProperties:false).
    Mutation: in _check_mode_payload, drop the strict-keys loop (`for k in ():`).
    Observed: a job carrying `promt`/`reepo` no longer flagged -> the test FAILs.
    Restored -> OK.
  Pin: test_each_mode_required_field.
    Mutation: drop a per-mode branch in _check_mode_payload (e.g. make `command`
    mode return []). Observed: a command job with no `command` passes -> FAIL.
  Pin: test_unknown_mode_rejected.
    Mutation: widen _JOB_MODES to include the bogus mode. Observed: pass -> FAIL.
"""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_tick():
    spec = importlib.util.spec_from_file_location("tick_fr42", _ROOT / "arunner" / "engine" / "tick.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load_tick()


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)       # an existing dir for repo
        self._n = 0

    def tearDown(self):
        self._tmp.cleanup()

    def _plan_file(self, plan):
        self._n += 1
        p = self.tmp / ("plan%d.json" % self._n)
        p.write_text(json.dumps(plan))
        return p

    def _agent(self, **kw):
        return dict({"id": "a", "repo": str(self.tmp), "mode": "agent",
                     "prompt": "do the work"}, **kw)

    def _command(self, **kw):
        return dict({"id": "c", "repo": str(self.tmp), "mode": "command",
                     "command": ["pytest", "-q"]}, **kw)

    def _log(self, **kw):
        return dict({"id": "l", "repo": str(self.tmp), "mode": "log",
                     "log_path": str(self.tmp / "build.log")}, **kw)

    def _shell(self, **kw):
        return dict({"id": "s", "repo": str(self.tmp), "mode": "shell",
                     "command": ["w", "--hb", "{HEARTBEAT_PATH}"]}, **kw)

    def _pipeline(self, **kw):
        return dict({"id": "p", "repo": str(self.tmp), "mode": "pipeline",
                     "steps": [{"mode": "agent", "prompt": "one"}]}, **kw)

    def _check(self, plan):
        return T.check_plan(self._plan_file(plan))


class ValidPlansPerMode(_Base):
    def test_every_mode_passes_clean(self):
        plan = {"schema_version": "2", "pool_size": 2,
                "jobs": [self._agent(), self._command(), self._log(),
                         self._shell(), self._pipeline()]}
        self.assertEqual(self._check(plan), [])


class CommonRequired(_Base):
    def test_missing_id(self):
        e = self._agent(); del e["id"]
        self.assertTrue(any("id" in p and "required" in p for p in self._check({"jobs": [e]})))

    def test_missing_repo(self):
        e = self._agent(); del e["repo"]
        self.assertTrue(any("repo" in p and "required" in p for p in self._check({"jobs": [e]})))

    def test_unknown_mode_rejected(self):
        e = self._agent(); e["mode"] = "wizard"
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("mode" in p and "wizard" in p for p in probs), probs)

    def test_missing_mode(self):
        e = self._agent(); del e["mode"]
        self.assertTrue(any("mode" in p for p in self._check({"jobs": [e]})))

    def test_nonexistent_repo(self):
        e = self._agent(repo="/no/such/dir/xyz")
        self.assertTrue(any("repo" in p and "existing directory" in p
                            for p in self._check({"jobs": [e]})))


class PerModeRequired(_Base):
    """Each mode's required field is enforced (capability-preservation guard)."""
    def test_each_mode_required_field(self):
        cases = [
            (self._agent(), "prompt", "agent mode needs a prompt or prompt_file"),
            (self._command(), "command", "command mode requires a non-empty array"),
            (self._log(), "log_path", "log mode requires a non-empty string"),
            (self._shell(), "command", "shell mode requires a non-empty array"),
            (self._pipeline(), "steps", "pipeline mode requires a non-empty array"),
        ]
        for job, field, msg in cases:
            bad = dict(job); bad.pop(field, None)
            probs = self._check({"jobs": [bad]})
            self.assertTrue(any(msg in p for p in probs),
                            "mode %s w/o %s: %s" % (job["mode"], field, probs))

    def test_agent_prompt_xor_prompt_file(self):
        (self.tmp / "p.md").write_text("from file")
        e = self._agent(prompt_file="p.md")              # both prompt and prompt_file
        probs = self._check({"jobs": [e]})
        self.assertTrue(any("exactly one of prompt / prompt_file" in p for p in probs), probs)

    def test_shell_requires_heartbeat_route(self):
        e = self._shell(command=["echo", "hi"])          # no {HEARTBEAT_PATH}
        self.assertTrue(any("HEARTBEAT_PATH" in p for p in self._check({"jobs": [e]})))


class StrictKeysTypoRejection(_Base):
    """additionalProperties:false — a typo'd key fails at --check (MUTATION PIN)."""
    def test_typo_key_rejected_per_mode(self):
        for builder, typo in ((self._agent, "promt"), (self._command, "comand"),
                              (self._log, "logpath"), (self._shell, "reepo")):
            e = builder(); e[typo] = "x"
            probs = self._check({"jobs": [e]})
            self.assertTrue(any("unknown key %r" % typo in p for p in probs),
                            "typo %r not rejected: %s" % (typo, probs))

    def test_known_key_on_wrong_mode_rejected(self):
        # log_path belongs to log mode; on an agent job it's an unknown key.
        e = self._agent(log_path="x")
        self.assertTrue(any("unknown key 'log_path'" in p for p in self._check({"jobs": [e]})))


class AnnotationSanctioned(_Base):
    """description/_comment validate at plan, job, and step level."""
    def test_annotation_passes_every_level(self):
        plan = {"description": "plan note", "_comment": "and an alias",
                "jobs": [self._agent(description="job note", _comment="x"),
                         self._pipeline(steps=[{"mode": "agent", "prompt": "one",
                                                "description": "step note", "_comment": "y"}])]}
        self.assertEqual(self._check(plan), [])


class CapabilityMappingCoverage(_Base):
    """Executable proof the collapse lost nothing: a fixture per preserved field
    validates under its mode."""
    def test_log_overlays(self):
        e = self._log(success_regex="OK", failure_regex="ERR",
                      sentinel_file=str(self.tmp / "done"), pid=4321,
                      command=["python3", "-c", "pass"])
        self.assertEqual(self._check({"jobs": [e]}), [])

    def test_command_heartbeat_path_and_auth_check(self):
        e = self._command(heartbeat_path="/abs/hb.ndjson", auth_check=["true"])
        self.assertEqual(self._check({"jobs": [e]}), [])

    def test_shell_auth_check_and_heartbeat_path(self):
        e = self._shell(auth_check=["true"], heartbeat_path="/abs/hb.ndjson")
        self.assertEqual(self._check({"jobs": [e]}), [])

    def test_vars_at_plan_job_step(self):
        # vars keys are lowercase by convention (UPPERCASE {TOKEN}s are reserved
        # engine placeholders; the typo-catch flags an unknown uppercase token).
        plan = {"vars": {"a": "1"},
                "jobs": [self._agent(vars={"b": "2"}),
                         self._pipeline(steps=[{"mode": "agent", "prompt": "use {b}",
                                                "vars": {"c": "3"}}])]}
        self.assertEqual(self._check(plan), [])

    def test_pipeline_step_gate_outcomes(self):
        e = self._pipeline(steps=[
            {"mode": "command", "command": ["true"],
             "gate": {"kind": "shell", "argv": ["true"],
                      "outcomes": {"0": "continue", "1": "halt", "2": "skip-to-next"}}}])
        self.assertEqual(self._check({"jobs": [e]}), [])

    def test_gate_outcomes_bad_value_rejected(self):
        e = self._pipeline(steps=[
            {"mode": "command", "command": ["true"],
             "gate": {"kind": "shell", "argv": ["true"],
                      "outcomes": {"0": "explode"}}}])     # not a closed-set outcome
        self.assertTrue(any("outcomes" in p and "explode" in p
                            for p in self._check({"jobs": [e]})))

    def test_adapter_activity_patterns(self):
        e = self._command(adapter_activity_patterns=["step \\d+", "building"])
        self.assertEqual(self._check({"jobs": [e]}), [])


class SchemaCheckAgreement(_Base):
    """Council-A round-2: --check and plan.schema.json agree on the gate-outcome
    closed set, gate/plan strict keys, the parametric skip-to-next, and vars
    numbers (each was a schema<->engine drift; now aligned)."""

    def _pipeline_gate(self, **gate):
        return self._pipeline(steps=[{"mode": "command", "command": ["t"],
                                      "gate": dict({"kind": "shell", "argv": ["t"]}, **gate)}])

    def test_gate_outcome_bad_value_rejected(self):
        probs = self._check({"jobs": [self._pipeline_gate(outcomes={"0": "frobnicate"})]})
        self.assertTrue(any("frobnicate" in p for p in probs), probs)

    def test_gate_parametric_skip_to_next_accepted(self):
        self.assertEqual(self._check({"jobs": [
            self._pipeline_gate(outcomes={"0": "skip-to-next:step-02", "1": "behavior-flag:fast"})]}), [])

    def test_gate_unknown_key_rejected(self):
        probs = self._check({"jobs": [self._pipeline_gate(bogus=1)]})
        self.assertTrue(any("gate" in p and "unknown key 'bogus'" in p for p in probs), probs)

    def test_plan_root_unknown_key_rejected(self):
        probs = self._check({"bogus_top": 1, "jobs": [self._agent()]})
        self.assertTrue(any("unknown top-level key 'bogus_top'" in p for p in probs), probs)

    def test_vars_number_value_accepted(self):
        self.assertEqual(self._check({"jobs": [self._agent(vars={"n": 123})]}), [])


class DefaultsMerge(_Base):
    def test_defaults_supply_missing_repo(self):
        plan = {"defaults": {"repo": str(self.tmp)},
                "jobs": [{"id": "a", "mode": "agent", "prompt": "x"}]}
        self.assertEqual(self._check(plan), [])

    def test_defaults_must_be_object(self):
        plan = {"defaults": [1, 2], "jobs": [self._agent()]}
        self.assertTrue(any("defaults" in p for p in self._check(plan)))


class PlanLevelAndReporting(_Base):
    def test_bad_toplevel_int(self):
        self.assertTrue(any("pool_size" in p for p in
                            self._check({"pool_size": 0, "jobs": [self._agent()]})))

    def test_missing_jobs(self):
        self.assertTrue(any("jobs" in p for p in self._check({"pool_size": 1})))

    def test_unknown_placeholder_typo_in_agent_prompt(self):
        e = self._agent(prompt="see {RUN_DOR}")           # typo'd token
        self.assertTrue(any("unknown placeholder {RUN_DOR}" in p
                            for p in self._check({"jobs": [e]})))

    def test_agent_bare_prompt_clean_no_placeholder_required(self):
        # The engine auto-injects the preamble, so a bare agent prompt with NO
        # placeholders is clean (the old "missing placeholder" rule is gone).
        self.assertEqual(self._check({"jobs": [self._agent(prompt="just do it")]}), [])

    def test_all_problems_reported_at_once(self):
        plan = {"pool_size": 0, "jobs": [
            {"id": "", "repo": "/no/such", "mode": "command"}]}  # bad pool, empty id, bad repo, no command
        probs = self._check(plan)
        classes = {
            "pool": any("pool_size" in p for p in probs),
            "id": any("jobs[0].id" in p for p in probs),
            "command": any("command mode requires" in p for p in probs),
            "repo": any("existing directory" in p for p in probs),
        }
        self.assertTrue(all(classes.values()), "%s -> %s" % (classes, probs))
        self.assertGreaterEqual(len(probs), 4)

    def test_bad_json_and_missing_file(self):
        bad = self.tmp / "bad.json"; bad.write_text("{not json")
        self.assertTrue(any("JSON" in p for p in T.check_plan(bad)))
        self.assertTrue(any("cannot read" in p for p in T.check_plan(self.tmp / "nope.json")))

    def test_exit_codes_and_report_via_main(self):
        good = self._plan_file({"jobs": [self._agent()]})
        bad = self._plan_file({"jobs": [self._agent(mode="rocket")]})
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
        src = (_ROOT / "arunner" / "engine" / "tick.py").read_text()
        self.assertNotIn("import jsonschema", src)
        self.assertNotIn("from jsonschema", src)


if __name__ == "__main__":
    unittest.main()
