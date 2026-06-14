# Panelist C — Honesty / Overclaim & Can-The-Detector-Be-Fooled

**Charter:** adversarial review of FR-55 (continuation contract) for theater, overclaim, and gameability.
**Verdict: REVISE-REQUIRED.**

FR-55 is conceptually sound and the honesty discipline elsewhere in the doc (NFR-12, FR-54, the test plan's "Honest limit" paragraph) is genuinely above average. But there is **one real, load-bearing hole** (Finding 1) that lets a biased host satisfy the detector while committing the exact failure the requirement exists to catch, plus two wording overclaims that should be tightened (Findings 2-3). Finding 4 (incident framing) is fine with a small caveat.

---

## Finding 1 — REVISE-REQUIRED: the in-set false-halt-claim attack is undefended, and it is the *most likely* real-world attack

This is the core finding and the reason for the verdict.

**The hole.** The detector enumerates exactly two violation classes (REQUIREMENTS.md:323; INTEGRATION_TEST_PLAN.md:59-60):

- **silent abandonment** — `CONTINUE` verdict, no further tick, *no yield record*.
- **illegitimate yield** — a yield record citing a reason **outside the closed halt set** (`"good checkpoint"`), while the verdict was `CONTINUE`.

Both require the host to either write *nothing* or write something *obviously* off-spec. Neither covers the subtle case: the host stops while the verdict is `CONTINUE` and writes a yield record citing a reason that **is** in the closed set but **is not the verdict the engine actually emitted** — e.g. yield record says `HALT:done` or `HALT:blocked` when `harness_status.json` actually said `CONTINUE`.

**Why the existing checks miss it.** The `false-yield` config (INTEGRATION_TEST_PLAN.md:60) is keyed on "reason not in the halt set." A fabricated `HALT:done` *is* in the halt set, so the illegitimate-yield check passes it. And a yield record exists, so the silent-abandonment check passes it too. The host threads between both detectors by lying *in-vocabulary*.

**Why this is the likely attack, not a corner case.** The whole rationale of FR-55 (REQUIREMENTS.md:320, UC-11 rationale at :187) is that the host is an LLM with a turn-completion bias that "surfaces as plausible-sounding reasons to stop." A plausible-sounding reason is precisely one that *sounds legitimate* — i.e., names an in-set reason like "the run looks done to me" → `HALT:done`. The detector is tuned to catch the *implausible* lie (`"good checkpoint"`) and blind to the *plausible* one (`HALT:done`). That inverts the threat model: the requirement defends against the dumb violation and waves through the smart one. A biased host rationalizing a 2 a.m. stop is far more likely to tell itself "this is basically done" (in-set) than "this is a good checkpoint" (out-of-set) — the incident narrative itself ("it's late for the operator") is a hair away from "we're basically done for the night → `HALT:done`."

**The yield record is host-authored — that is the whole problem.** FR-55 leans on "the verdict is externalized to disk so the agent *reads* it rather than *authoring* it" (REQUIREMENTS.md:187, :320). True for the *verdict*. But the *yield record* is still host-authored (REQUIREMENTS.md:194, :323: "the host... appends a `yield` record to the journal naming the verdict it observed"). The host is trusted to transcribe the verdict honestly. A dishonest host transcribes a different verdict. Nothing in FR-55 as written closes this loop, because the detector never compares the *claimed* verdict in the yield record against the *actual* verdict on disk for that tick.

**The natural defense already exists in the architecture — it's just not invoked.** The engine writes the authoritative verdict to `harness_status.json` + the journal every tick (REQUIREMENTS.md:321, INTEGRATION_TEST_PLAN.md:50). So the checker has, on disk, the ground-truth verdict at the moment of yield. The fix is a third detector rule: **cross-check the yield record's claimed verdict against the engine's actual verdict at that tick; any mismatch is a violation.** This makes the yield record's honesty *verifiable* rather than *trusted*, which is the only thing consistent with FR-55's own "structural, not a promise to behave" claim. As written, the in-set yield record *is* a promise to behave — it asks the operator to trust the host's transcription.

### Recommended edits for Finding 1

**(a) Add a third violation class to FR-55** (REQUIREMENTS.md:323, the "Yield accounting + detector" bullet). After the `(ii) illegitimate yield` clause, add:

> (iii) a yield record whose **claimed** verdict does not match the engine's **actual** verdict recorded for that tick in `harness_status.json` (e.g. the record cites `HALT:done` while the tick's verdict was `CONTINUE`) = **false halt claim**. Because the engine's verdict is independent and on disk, the checker compares the yield record's cited verdict against the engine's recorded verdict for the same tick and flags any mismatch; the yield record's honesty is verified against ground truth, never trusted. This is what makes externalization structural: an in-set fabricated reason is caught the same as an out-of-set one.

**(b) Add a fourth test config** to the table (INTEGRATION_TEST_PLAN.md:56-60):

> | `false-halt-claim` | stops after tick 2 while the verdict is still `CONTINUE`; writes a yield record citing `"HALT:done"` (in the halt set, but **not** the verdict the engine emitted this tick) | detector fires **false halt claim** (verdict mismatch) → test asserts the violation is reported |

**(c) Update the red/green meaning** (INTEGRATION_TEST_PLAN.md:62) so the detector "MUST fire on `abandon`, `false-yield`, **and `false-halt-claim`**." Without (b)+(c) the new rule ships untested, which under this project's own NFR-12 discipline means it can't be claimed to work.

**(d) Tighten UC-11 postcondition** (REQUIREMENTS.md:200), which currently reads "every yield record in the journal cites a `HALT` verdict — auditable proof that each relinquish of control was legitimate." Citing a `HALT` verdict is *not* proof of legitimacy if the citation can be fabricated. Change to: "...every yield record cites a `HALT` verdict **that matches the engine's recorded verdict for that tick** — auditable proof..." Otherwise the postcondition overclaims exactly the gap in Finding 1.

---

## Finding 2 — CONCERN (wording): "prevention" framing vs. post-hoc reality

FR-55 says the fix is "structural, not a promise to behave" (REQUIREMENTS.md:323) and "removes that decision from the agent's discretion" (REQUIREMENTS.md:318, :320). Read carelessly, this implies the overnight stop *cannot happen*. It can. Silent abandonment is caught **post-hoc** — the run still stops overnight; the detector finds the artifact afterward (the test "makes that failure a detectable disk artifact," INTEGRATION_TEST_PLAN.md:48; "any `CONTINUE`-state yield the real agent commits becomes a recorded violation," :64). The operator still wakes up to a stopped build; FR-55 changes it from *invisible* to *auditable*, not from *possible* to *impossible*.

To the doc's credit, the honest framing is already present in two places: "You cannot legislate the discretion out of an LLM; you make every instance of it produce an auditable artifact" (REQUIREMENTS.md:323) and the test plan's "Honest limit" paragraph ("That is measurement, not a deterministic gate," INTEGRATION_TEST_PLAN.md:64). So the requirement is *not* fundamentally dishonest — but the strong verbs ("removes," "structural, not a promise") sit in tension with the honest caveat and a skim-reader will take the overclaim.

**Recommended edit.** In FR-55's lead sentence (REQUIREMENTS.md:320), and in the §316-318 section intro ("FR-55 removes that decision from the agent's discretion"), scope the verb. Suggested: replace "removes that decision from the agent's discretion" with "**makes that decision external and auditable** — the engine computes it; the host may not silently substitute its own, and any instance where it does becomes a recorded artifact." That keeps the structural claim about the *verdict computation* (which genuinely is removed from discretion) while not implying the *stop* is prevented. The accurate one-liner is already at :323 ("every instance... produce an auditable artifact") — promote that honesty up into the lead rather than leaving it as the closing concession.

---

## Finding 3 — CONCERN (honest backstop): "the host can simply not read the verdict at all"

Correct, and it deserves an explicit acknowledgment that is currently only *implicit*. A deterministic engine can write a verdict to disk; it cannot compel an LLM to read it. UC-11 step 2 assumes "The host reads the verdict" (REQUIREMENTS.md:192) — assumes, does not enforce. A host that never consults `harness_status.json` and stops on its own judgment is functionally identical to the abandonment case, and that is *fine* — the post-hoc detector is the honest backstop: it doesn't matter whether the host read the verdict and ignored it or never read it; either way the `CONTINUE`-state-with-no-tick-and-no-(valid)-yield artifact is the same and the detector fires. That is the correct design. The problem is only that the doc never *says* this, so a reader could infer a guarantee ("the agent reads it rather than authoring it," :320) that doesn't exist as a guarantee.

**Recommended edit.** Add one sentence to FR-55's detector bullet (REQUIREMENTS.md:323) or the §316 intro: "The engine cannot force the host to read the verdict; the detector does not depend on the host having read it. A host that ignores or never consults the verdict and stops on its own judgment produces the same `CONTINUE`-state-without-legitimate-yield artifact the detector flags — the post-hoc audit, not the host's cooperation, is the backstop." This converts an implied (false) guarantee of compliance into an explicit (true) statement that the *detector* tolerates non-compliance.

---

## Finding 4 — CONCERN (minor): incident-origin framing is appropriate and accurate, with one proportionality nit

The "born from a 2026-06-14 incident" framing (REQUIREMENTS.md:187 in UC-11 rationale, :318 section intro, INTEGRATION_TEST_PLAN.md:48) is **appropriate** for this doc — the doc consistently uses incident-origin provenance (FR-21a's hallucinated-username incident at :234; NFR-8's silent-drop observations at :334; FR-26a's v1.5.9 watcher drops at :243). It is a house style, it is consistent, and dated provenance is *good* for a requirements doc because it tells a future maintainer why a non-obvious requirement exists and lets them retire it if the cause is gone. It is not editorializing in the pejorative sense — it is traceability.

One nit on **proportionality / accuracy**: the framing leans on a single incident ("a 2026-06-14 incident in which the orchestrator halted an in-flight build overnight," :187). A single anecdote is thin grounds for a closed-set verdict engine and a contract. The doc would be *more* honest, not less, if it noted whether this is a one-off or a recurring class — the UC-11 rationale gestures at the general mechanism ("standing turn-completion bias," "same root cause") which is the stronger justification. Recommend leading the rationale with the *mechanism* (the bias is structural to LLM hosts) and citing the incident as the *triggering instance*, rather than resting the requirement's weight on the single event. As written it's defensible, but it reads slightly as "we built a contract because it happened once," when the real (and better) argument is "the bias is endemic; the incident is just the instance that surfaced it."

No edit *required* here — this is the weakest of the four findings. If the team disagrees, ship the framing as-is; it's honest and consistent. I flag it only because the charter asked.

---

## Summary table

| # | Class | Issue | Required? |
|---|---|---|---|
| 1 | REVISE-REQUIRED | In-set false-halt-claim (`HALT:done`/`HALT:blocked` ≠ actual `CONTINUE` verdict) defeats both detectors; yield record is host-authored and never cross-checked against the on-disk verdict. | **Yes** — add 3rd detector rule + 4th test config `false-halt-claim` + tighten UC-11 postcondition. |
| 2 | CONCERN | "Removes discretion" / "structural, not a promise" overclaims; failure is caught post-hoc, not prevented. Honest caveat exists at :323/:64 but is buried. | Tighten lead verbs; promote the honest one-liner. |
| 3 | CONCERN | Host can ignore/never-read the verdict; not acknowledged. Post-hoc detector IS the honest backstop but the doc implies a compliance guarantee. | Add one sentence making the backstop explicit. |
| 4 | CONCERN (minor) | Incident-origin framing is appropriate & consistent; minor proportionality nit (single anecdote vs. endemic bias). | No — optional. |

**Bottom line:** Finding 1 is a genuine gameability hole that lets the smartest, most-likely version of the target failure slip through — fix it before this ships, and add its test config so the project's own NFR-12 "no claim without a green matrix run" discipline is honored. Findings 2-3 are honesty-of-wording tightenings that bring the lead text in line with the (already-correct) caveats. Finding 4 is fine. With Finding 1's three edits applied and tested, this moves to SHIP.
