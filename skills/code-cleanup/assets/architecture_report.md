# Architecture Recovery Report

Scale depth to the project: fill sections that have findings, omit empty ones — but always include the
Multi-Hop / Call-Path Audit, Cross-Entry Duplicates, and Dead-Code Candidates sections (state "none found"
explicitly rather than dropping them).

## Executive Summary

## Current Project Structure

```txt
PASTE_GROUPED_TREE_HERE
```

## Runtime Entry Points

| Entry Point | Purpose | Called By | Risk | Notes |
| ----------- | ------- | --------- | ---- | ----- |

## Main Execution Flows

```txt
ENTRY_POINT
  -> MODULE.FUNCTION
    -> MODULE.FUNCTION
```

## Multi-Hop / Call-Path Audit

For each major feature, the call path with every hop classified (KEEP / MERGE / DELETE / RENAME / MOVE /
TEST FIRST) and node-tagged (entry / wiring / domain / I/O). Record total vs meaningful hop counts.

```txt
Feature: <name>
Before:
  entry.fn()                    KEEP   entry
    -> wrapper.fn()             MERGE  wiring   (forwards only)
    -> factory.get()           DELETE wiring   (one impl)
    -> service.run()           KEEP   domain
    -> store.put()             KEEP   I/O
  Hops: 5 (meaningful: 3)
After (target):
  entry.fn() -> service.run() -> store.put()
  Hops: 3 (meaningful: 3)
```

| Feature | Hops Before | Hops After | Meaningful Before/After | Notes |
| ------- | ----------: | ---------: | ----------------------- | ----- |

### Cross-Entry Duplicates / Parallel Entries

Swept across ALL public entrypoints (not only the named area): two public entries delegating to one impl, or a
registry/factory resolving to a single impl. Any KEEP needs a load-bearing proof.

| Entry A | Entry B / Registry | Resolves to | Verdict (delete dup / inline / keep) | Load-bearing proof (if keep) |
| ------- | ------------------ | ----------- | ------------------------------------ | ---------------------------- |

## File Classification

| File Path | Responsibility | Imported By | Imports | Entry Point? | Risk | Recommended Location | Action |
| --------- | -------------- | ----------- | ------- | ------------ | ---- | -------------------- | ------ |

## Dependency Hotspots

| File | Fan-In | Fan-Out | Problem | Recommendation |
| ---- | -----: | ------: | ------- | -------------- |

## Circular Dependencies

| Cycle | Risk | Recommendation |
| ----- | ---- | -------------- |

## Dead-Code Candidates

| File / Symbol | Evidence | Confidence | Safe Action |
| ------------- | -------- | ---------: | ----------- |

## Architecture Problems

## Target Architecture

```txt
PASTE_TARGET_TREE_HERE
```

## Migration Plan

## Verification Plan

## Risks and Unknowns
