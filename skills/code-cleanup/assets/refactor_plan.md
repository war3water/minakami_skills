# Behavior-Preserving Refactor Plan

## Goal

## Non-Goals

## Constraints

## Net-Hop Target

| Touched Feature | Meaningful Hops Before | Target After | Must Not Exceed |
| --------------- | --------------------: | -----------: | --------------- |

Every touched feature's meaningful-hop count after ≤ before. No permanent compatibility layers remain.

## Stage 0: Documentation Only

### Changes

### Files

### Risk

### Verification

## Stage 1: Static Analysis Tooling

### Changes

### Files

### Risk

### Verification

## Stage 2: Architecture Rules

### Changes

### Files

### Risk

### Verification

## Stage 3: Low-Risk Moves (directness-first)

### Changes

### Files

### Fallbacks (only if consumers non-enumerable; with removal trigger)

### Risk

### Verification

## Stage 4: Medium-Risk Simplification

### Changes

### Files

### Risk

### Verification

## Stage 5: Core Refactor

### Changes

### Files

### Risk

### Verification

## Stage 6: Retire Fallbacks

### Compatibility layers removed

## Approval Required

Every approval-tier item (SKILL.md Deletion gates), one row each — approving this plan authorizes exactly
these and nothing more. An item not listed here is not approved by this plan.

| Item | Kind (deletion / shim retirement / public-surface rename / behavior-defining test change) | Evidence | Stage |
| ---- | ---- | ---- | ---- |
