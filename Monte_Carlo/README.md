# Monte_Carlo

This folder is the root-level entry point for the Monte Carlo approach in this repo.

The actual runtime implementation still lives inside `main`, but these are the files you will usually want to edit first:

- API route: `main/apps/api/app/api/routes/monte_carlo.py`
- API service: `main/apps/api/app/services/monte_carlo.py`
- Search config example: `main/configs/monte_carlo_search.example.json`
- n8n workflow: `main/automation/n8n/timestamp-msi-monte-carlo-pipeline.json`
- validation workflow: `main/automation/n8n/timestamp-msi-monte-carlo-validation.json`
- UI mode wiring: `main/apps/web/src/components/msi-workbench.tsx`

This keeps Monte Carlo easy to find at the repo root without duplicating the working code.
