# 4basecare MSI Web

This frontend is now a single dashboard, not the older four-mode workstation.
The active UI is the `TCGA DX1 MSI Runner` rendered from:

- `src/app/page.tsx`
- `src/components/msi-workbench.tsx`

## What The Current UI Does

- checks backend health
- launches a TCGA DX1 bundle
- refreshes live bundle status every 15 seconds
- reads the latest archive summary
- shows label balance with D3
- shows approach metrics with Recharts
- keeps the latest `bundle_id` in local storage

The current page talks only to the FastAPI backend. It does not expose the old
multi-surface workstation behavior described in earlier docs.

## Backend Endpoints Used By The UI

```text
GET  /health
POST /approach-2/pipeline/train-tcga-slide-triad
GET  /approach-2/pipeline/train-tcga-slide-triad-latest
GET  /approach-2/pipeline/tcga-batch-archive-latest
```

The API base defaults to:

```text
http://127.0.0.1:8001
```

Override with:

```text
NEXT_PUBLIC_MSI_API_URL=http://127.0.0.1:8001
```

## Run

```powershell
cd <repo-root>\main\apps\web
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

## Current UX Notes

- the page uses the `snow-theme`
- the active visual system is light, clinical, and single-purpose
- the hero copy and metrics cards are specific to the DX1 TCGA pipeline
- older VM-control copy in previous docs is no longer the main UI contract

## Important Files

- `src/components/msi-workbench.tsx`: current dashboard logic and visuals
- `src/app/page.tsx`: page shell
- `src/app/globals.css`: theme and shared styling
- `public/assets/4basecare-mars.png`: hero image

## Validation

```powershell
cd <repo-root>\main\apps\web
npm.cmd run lint
npm.cmd run build
```
