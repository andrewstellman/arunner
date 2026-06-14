"""13a — packaging invariants (FR-33/34): the engine ships inside the wheel so
the installed console script works, and the npm package is an honest thin
launcher (not a fake Node CLI).

These are STRUCTURAL guards (no network, no build) that pair with the actual
publish-safety gates RUN out-of-band (clean-clone cold build + throwaway-venv
install + smoke, recorded in outputs/034). They keep the source tree from
drifting back into a state where `pip install arunner` yields a broken CLI.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ENGINE_MODS = ("tick", "ticker", "heartbeat", "jobs", "incontext",
                "demo_worker")


class EngineShipsInPackage(unittest.TestCase):

    def test_engine_is_a_subpackage_with_all_modules(self):
        eng = _ROOT / "arunner" / "engine"
        self.assertTrue((eng / "__init__.py").is_file(),
                        "arunner/engine must be an importable subpackage")
        for m in _ENGINE_MODS:
            self.assertTrue((eng / ("%s.py" % m)).is_file(),
                            "engine module missing from the package: %s" % m)

    def test_pyproject_packages_include_the_engine(self):
        # if arunner.engine isn't in [tool.setuptools] packages, the wheel
        # ships a CLI that can't find its engine -> installed `arunner run` 500s.
        txt = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r"(?ms)^packages\s*=\s*\[(.*?)\]", txt)
        self.assertIsNotNone(m, "pyproject has no setuptools packages list")
        pkgs = m.group(1)
        self.assertIn('"arunner"', pkgs)
        self.assertIn('"arunner.engine"', pkgs)

    def test_all_three_console_scripts_are_declared(self):
        # the docs (README/TOOLKIT) promise `arunner`, `arunner-ticker`, and
        # `arunner-heartbeat` -- each must map to a real entry point so the
        # documented commands actually exist once installed.
        txt = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('arunner = "arunner.cli:main"', txt)
        self.assertIn('arunner-ticker = "arunner.engine.ticker:main"', txt)
        self.assertIn('arunner-heartbeat = "arunner.engine.heartbeat:main"', txt)

    def test_no_legacy_bin_dir_with_engine_modules(self):
        # the engine moved out of bin/ into the package; a stray bin/tick.py
        # would silently shadow nothing but signals an incomplete move.
        for m in _ENGINE_MODS:
            self.assertFalse((_ROOT / "bin" / ("%s.py" % m)).exists(),
                             "engine module still in bin/: %s" % m)


class NpmLauncherIsHonest(unittest.TestCase):

    def setUp(self):
        self.js = (_ROOT / "npm-bin" / "arunner.js").read_text(encoding="utf-8")

    def test_delegates_to_python_module(self):
        # it must EXEC the Python package, not reimplement the CLI in Node.
        self.assertIn('"-m", "arunner"', self.js)
        self.assertIn("spawnSync", self.js)

    def test_points_at_pipx_when_python_pkg_absent(self):
        self.assertIn("pipx install arunner", self.js)

    def test_no_stale_placeholder_claim(self):
        # the retired 0.0.1 "pre-release placeholder" string must be gone, and
        # it must not pretend to be a standalone Node CLI.
        low = self.js.lower()
        self.assertNotIn("placeholder", low)
        self.assertNotIn("0.0.1", self.js)


if __name__ == "__main__":
    unittest.main()
