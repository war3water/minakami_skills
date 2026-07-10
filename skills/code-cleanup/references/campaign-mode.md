# Campaign Mode — Continuous Cleanup

Campaign mode is the continuous operating model: instead of *analyze → report → stop*, it runs a bounded,
evidence-gated loop that keeps working prioritized cleanup across rounds until the codebase reaches an agreed
end state. The thing that persists across rounds is a **backlog ledger**, not the agent's discretion. Loaded
with `safety.md` when the user requests a deep / ongoing cleanup. Self-contained for the loop; each round
re-enters the Diagnosis / Execution / deletion stages and loads their files per the SKILL.md manifest.

---

## 1. When campaign mode applies

Selected at intake (SKILL.md); establish the ledger + scope contract, then run the loop in §3 to
convergence. A multi-objective brief is decomposed at intake: each objective (docs, dead code, deprecated
files, test consolidation, modularity) becomes one or more ledger items. In campaign mode the hotspot
*narrowing* is waived — the loop drives toward full coverage (§2), with churn used only to order work
(`discovery.md`).

---

## 2. Coverage guarantee

1. **Complete inventory up front** — list every source file and rank it (churn × LoC, or LoC × complexity ×
   fan-in when history is unavailable). Cheap; names and metrics only, not deep reads.
2. **Progressive deep coverage tracked in the ledger** — begin with the highest-value files, but record every
   file's review state so "what has not yet been deeply reviewed" is always explicit.

Start narrow; never stay narrow silently (structure-first, git only orders — `discovery.md`).

---

## 3. The campaign loop

```text
intake → establish ledger + scope contract
  ↓
[ROUND]
  1. SURVEY        inspect the repo directly (map / call-graph hop audit / reachability / design checks);
                   admit only evidence-gated items to the ledger (§5). Git history is not the discovery lens.
  2. PRIORITIZE    rank the ledger by ROI = (maintenance-friction × blast-radius-reduction) / risk;
                   churn only orders found problems — cold-code problems are never filtered out.
  3. EXECUTE       work the top items this round (a batch, not one-then-stop):
                     - one logical change per boundary; no tangling (safety.md §2)
                     - directness-first; prefer deterministic engines; verify each; revert-on-red
                     - items above the auto tier are checkpointed (§4), not executed
  4. PARK          issues surfaced mid-work are recorded as out-of-scope items; not chased this round
  5. UPDATE        mark items done / soaking; refresh coverage; write the ledger
  6. CONVERGE?     stop on a dry round, budget limit, or the agreed end state (§9); else next ROUND
```

---

## 4. Scope contract and risk tiers

Agreed once at campaign start; the loop runs inside it without per-step prompting — autonomy on reversible
work, checkpoints on the irreversible. Use the `safety.md` §1 tiers as-is (low → auto; medium → auto within
the round's file budget; high → always checkpoint). The scope contract sets the budgets — max files per round,
max rounds before a mandatory summary, optional time/token caps — which bound the loop and act as runaway
detectors (blocking the failure modes in `glossary.md` bibliography).

---

## 5. Evidence gate and parking

**Evidence gate.** Every ledger item must cite a concrete signal — a dead reference, a smell/metric over
threshold, an untraceable call path, a duplicate-with-drift, a failing/oversized test, an outdated doc
claim. Items justified only by taste are rejected (no style-only churn).

**Parking.** When a change surfaces a new issue, record it as an out-of-scope ledger item, finish the current
safe increment, and reconsider it in the next round's SURVEY. Do not follow the thread mid-change.

---

## 6. The ledger

The durable record; a fresh session reads it and resumes without prior context.

- **Storage:** a tracked `CLEANUP_LEDGER.md` in the agent-work directory (location + placement rules:
  SKILL.md loading-manifest section; commit only when the user asks). Small repos use a lightweight
  in-conversation backlog instead of adding a tracking file to a tiny tree.
- **Format:** Markdown. Skeleton in `assets/cleanup_ledger.md` — copy from it.
- **Status lifecycle:** `proposed → approved → in-progress → done`; deletes pass through `soaking` (§8);
  `rejected` (evidence insufficient / duplication intentional); `parked` (out-of-scope, revisited in SURVEY).

---

## 7. Safety invariants

Campaign mode adds no new safety surface: apply `safety.md` in full, per item, every round.

---

## 8. Deletion soak across rounds

Continuation is what makes safe deletion executable; a single pass cannot tombstone-then-delete.

- A delete candidate enters `soaking`: tombstone the symbol or file — **log-and-delegate, behavior preserved**
  (`techniques.md` §6 step 5) — in round *N*.
- Hard-delete only in a later round, after the soak yields **new evidence from a named observation source**
  (the tombstone's log fired nowhere across real runs; a run of the golden / extension paths; external usage
  re-checked) — not merely a second static survey, which repeats round *N*'s reasoning and adds no signal.
- Soak is measured by **tombstone + one later-round confirmation from that source**, not wall-clock — an
  engagement has no release cadence. The full Safe-Deletion Playbook (`techniques.md` §6) still governs each
  deletion.

---

## 9. Termination

Stop, and emit a summary, when any holds: **dry round** (a full SURVEY admits no new qualifying item);
**budget limit** (max rounds / files / time — summarize and ask whether to extend); **agreed end state
reached** (the acceptable end state in the ledger header). Target the agreed end state, never "perfect."
Non-idempotent oscillation (A → B → A across rounds) signals churn and is treated as a dry round.

**Drain the soak queue before the final summary.** No `soaking` item may be left tombstoned at termination —
for each, either the soak confirmed it dead (hard-delete) or it did not (revert the tombstone to live and
downgrade the item to `parked`). Do **not** open a new soak in a round with no later round budgeted;
keep-and-flag such deletes instead. A left-behind tombstone is itself a permanent "temporary" artifact
(SKILL.md success criterion 4), so termination is not reached while one stands.

---

## 10. Execution model (honest limits)

"Keep going" operates at three levels:

- **Within a turn** — EXECUTE works the whole prioritized batch (verifying between items), not one then stop.
- **Across sessions** — the tracked ledger file makes resumption stateless: a fresh invocation reads it and
  continues, no reliance on conversation memory.
- **Unattended recurrence** — handled by an external scheduler if the host provides one (e.g. the harness
  `/loop` feature); campaign mode does not depend on it.
