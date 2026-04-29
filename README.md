# 4basecare-MSI

This branch uses `E:\4basecare-MSI` as the main workspace root and keeps the MSI work split into clear top-level modules instead of hiding everything inside one app folder.

## Main Structure

```text
4basecare-MSI/
  Approach_1/     Timestamp_msi workstation and orchestration app
  Approach_2/     standalone end-to-end MSI platform scaffold
  Monte_Carlo/    dedicated index for Monte Carlo flow, configs, and workflow entry points
  extras/         lazyslide and slideflow basic notebooks / starter experiments
  datasets/       local-only datasets and raw archives (not pushed to GitHub)
  shared_assets/  diagrams and architecture visuals
```

## Three Defined Approaches

### 1. Approach_1

The active `Timestamp_msi` workstation on the `complex-triad` branch. This is the premium local UI plus FastAPI orchestration surface and still contains the integrated workflow modes for:

- Approach 1 baseline orchestration
- Approach 2 route mounting / triad runner support
- Monte Carlo validation and experiment analysis
- Parallel metrics comparison

Primary code lives in:

- `Approach_1/apps/api`
- `Approach_1/apps/web`
- `Approach_1/automation`

### 2. Approach_2

The separate end-to-end MSI prediction platform scaffold with its own backend, frontend, and studio runtime:

- `Approach_2/backend`
- `Approach_2/frontend`
- `Approach_2/studio`

Use this when you want to work directly on the standalone platform structure instead of the integrated `Timestamp_msi` workstation.

### 3. Monte_Carlo

This folder is the clean entry point for the Monte Carlo approach so it is easy to find without digging through the integrated app. It documents the exact files that power the Monte Carlo mode inside `Approach_1`.

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
