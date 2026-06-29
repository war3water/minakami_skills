# Campaign Mode — Continuous Cleanup

Campaign mode is the continuous operating model: instead of *analyze → report → stop*, it runs a bounded,
evidence-gated loop that keeps working prioritized cleanup across rounds until the codebase reaches an agreed
end state. The thing that persists across rounds is a **backlog ledger**, not the agent's discretion. Loaded
with `safety.md` when the user requests a deep / ongoing cleanup. Self-contained.

---

## 1. When campaign mode applies

SKILL.md's intake selects campaign mode for a deep / exhaustive / whole-repo request, a multi-objective
brief, or an explicit "keep going" — then establishes a ledger + scope contract and runs the loop in §3 to
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

Start narrow; never stay narrow silently. Problems are found by reading the repo, not git logs
(`discovery.md` — structure-first, git only orders).

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

- **Storage:** a tracked `CLEANUP_LEDGER.md` in a skill-named agent-work directory (default `.agent_works/code-cleanup/`, kept out of the project's core code and `docs/`; repo root only if the user wants it highly visible) for campaign work on medium/large repos
  (survives sessions, reviewable in diffs; commit it only when the user asks — `safety.md`). Small repos use a lightweight in-conversation backlog instead, to
  avoid adding a tracking file to a tiny tree. This is purely *where the ledger is stored* — unrelated to the
  analysis method.
- **Format:** Markdown. Skeleton in `assets/cleanup_ledger.md` — copy from it.
- **Status lifecycle:** `proposed → approved → in-progress → done`; deletes pass through `soaking` (§8);
  `rejected` (evidence insufficient / duplication intentional); `parked` (out-of-scope, revisited in SURVEY).

---

## 7. Safety invariants

Campaign mode adds no new safety surface; it applies `safety.md` per item, every round: revert-on-red
(agent-owned-files rollback); one logical change per boundary, no tangling; deterministic engine performs
the edit; verify between items; macro work as a Mikado graph, one leaf at a time; directness-first with no
permanent fallbacks.

---

## 8. Deletion soak across rounds

Continuation is what makes safe deletion executable; a single pass cannot tombstone-then-delete.

- A delete candidate enters `soaking`: tombstone the symbol or file (`techniques.md` §8 step 5) in round *N*.
- Hard-delete only in a later round, after a re-survey surfaces no consumer.
- Soak is measured by **tombstone + one later-round confirmation**, not wall-clock — an engagement has no
  release cadence. The full Safe-Deletion Playbook (`techniques.md` §8) still governs each deletion.

---

## 9. Termination

Stop, and emit a summary, when any holds: **dry round** (a full SURVEY admits no new qualifying item);
**budget limit** (max rounds / files / time — summarize and ask whether to extend); **agreed end state
reached** (the acceptable end state in the ledger header). Target the agreed end state, never "perfect."
Non-idempotent oscillation (A → B → A across rounds) signals churn and is treated as a dry round.

---

## 10. Execution model (honest limits)

"Keep going" operates at three levels:

- **Within a turn** — EXECUTE works the whole prioritized batch (verifying between items), not one then stop.
- **Across sessions** — the tracked ledger file makes resumption stateless: a fresh invocation reads it and
  continues, no reliance on conversation memory.
- **Unattended recurrence** — handled by the harness `/loop` feature when the user wants it; campaign mode
  does not depend on it.
