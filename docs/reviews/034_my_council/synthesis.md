# 13a (iteration 034) — my independent release-gate council — SYNTHESIS

*Cowork's own 3-panel release-gate review, independent of the worker's self-Council. Run 2026-06-14 against HEAD `6dc8016`.*

## Verdict: unanimous SHIP (3/3)

| Panelist | Charter | Verdict | How verified |
|---|---|---|---|
| A | Console script & version single-source | **SHIP** | Built the wheel, installed into a throwaway venv, ran installed `arunner --version` → `0.1.0` and `arunner --help` (8 verbs); `_reserve` grep-clean except the retirement guard; drift test mutation-**bites** (diverged pyproject → AssertionError). |
| B | Publish-safety evidence (FR-33) | **SHIP** | Independently reproduced all 4 gates from a clean copy: build sdist+wheel + `twine check` PASSED; throwaway-venv install + bundled-demo to `done` via installed scripts; `npm publish --dry-run` clean (arunner@0.1.0, 4 files); no `twine upload`/real `npm publish`; commits local-only (not on origin). |
| C | Distribution honesty | **SHIP** | (ran earlier) npm thin-launcher honest, no false Node-CLI claim; name/version `arunner`/`0.1.0` consistent across pyproject, package.json, plugin.json, marketplace.json, SKILL. |

This corroborates the worker's own 3-panel (which also caught and fixed a stale PyPI description parenthetical before SHIP).

## Non-blocking follow-ups (do NOT gate the ship; track for v0.1.x)

1. **Default runs-root is package-relative.** Installed `arunner run` wrote to `…/site-packages/harness_runs/`, and `ARUNNER_RUNS_ROOT` was not honored in the installed smoke. The run completed correctly, but the default should be CWD/XDG, not inside site-packages. (Both panelists flagged independently.)
2. **Bundled demo not carried in the wheel.** No `MANIFEST.in`; the demo plan's `target_repo` paths are placeholders, so the demo runs from the source tree, not the installed package. The installed package itself works; the demo is just not shipped. A `MANIFEST.in` + concretized demo would let an adopter run the demo straight from `pip install`.

## Bottom line

13a is shippable. The 0.1.0 artifacts are real and verified upload-ready; publishing remains the operator's gated action. The two follow-ups are quality-of-life for the first adopter, not release blockers.
