# Monte_Carlo

This folder is the root-level entry point for the Monte Carlo approach in this repo.

The actual runtime implementation still lives inside `Approach_1`, but these are the files you will usually want to edit first:

- API route: `Approach_1/apps/api/app/api/routes/monte_carlo.py`
- API service: `Approach_1/apps/api/app/services/monte_carlo.py`
- Search config example: `Approach_1/configs/monte_carlo_search.example.json`
- n8n workflow: `Approach_1/automation/n8n/timestamp-msi-monte-carlo-pipeline.json`
- validation workflow: `Approach_1/automation/n8n/timestamp-msi-monte-carlo-validation.json`
- UI mode wiring: `Approach_1/apps/web/src/components/msi-workbench.tsx`

This keeps Monte Carlo easy to find at the repo root without duplicating the working code.
