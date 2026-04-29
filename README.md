# 4basecare-MSI

This branch uses `E:\4basecare-MSI` as the main workspace root and keeps the MSI work split into clear top-level modules instead of hiding everything inside one app folder.

## Main Structure

```text
4basecare-MSI/
  Approach_1/     Timestamp_msi workstation and orchestration app
  Monte_Carlo/    dedicated index for Monte Carlo flow, configs, and workflow entry points
  extras/         lazyslide and slideflow basic notebooks / starter experiments
  datasets/       local-only datasets and raw archives (not pushed to GitHub)
  shared_assets/  diagrams and architecture visuals
```

## Final Structure

### 1. Approach_1

The active `Timestamp_msi` workstation on the `complex-triad` branch. This is the main product in the repo and contains the integrated workflow modes for:

- Approach 1 baseline orchestration
- Approach 2 internal platform mode and triad runner support
- Monte Carlo validation and experiment analysis
- Parallel metrics comparison

Primary code lives in:

- `Approach_1/apps/api`
- `Approach_1/apps/web`
- `Approach_1/automation`

### 2. Monte_Carlo

This folder is the clean entry point for the Monte Carlo approach so it is easy to find without digging through the integrated app. It documents the exact files that power the Monte Carlo mode inside `Approach_1`.

## About Approach 2

There is no longer a separate top-level `Approach_2` folder in the final repo.

Approach 2 still exists as a working mode, but its real code now lives inside the main app:

- `Approach_1/apps/api/app/approach_2`
- `Approach_1/apps/web/src/components/msi-workbench.tsx`

That keeps the repo final and cleaner while preserving the Approach 2 API/UI flow.

## Extras

`extras/` is intentionally separate from the three main approaches. It contains the basic experiments you wanted visible in the repo:

- `extras/lazyslide_basics`
- `extras/slideflow_basics`

## Datasets

`datasets/` holds the local patch dataset and raw archives. These are kept out of GitHub because they are too large for a normal repo push, but the folder is preserved in the workspace so the apps still know where to find them locally.

Current local dataset path used by the triad runner:

```text
E:\4basecare-MSI\datasets\CRC-VAL-HE-7K
```

## Branch

This root now follows the Git history and remote of:

```text
https://github.com/martian3062/Timestamp_msi
branch: complex-triad
```
