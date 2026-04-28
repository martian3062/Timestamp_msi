# 4basecare MSI Workbench

Browser-side workstation for the TCGA colorectal MSI project. The app now has a
three-way switch for Approach 1, Approach 2, and Monte Carlo so the user can
move between manual VM orchestration, the imported platform backend, and
stochastic validation without leaving the main screen.

For the full project-level guide and backend API details, see the root
`README.md`.

## What It Does

- Upload an MSI annotation CSV and detect patient, slide, label, and fold fields.
- Upload a GDC manifest CSV/TSV and detect file id plus filename fields.
- Compute label mix and fold balance directly from the uploaded files.
- Check the pathology VM over SSH from the local Next API.
- Browse the VM project folder, upload selected annotation/manifest files to it,
  start the GDC downloader, start Jupyter, and open the local tunnel.
- Use Approach 2 controls for preprocessing, feature extraction, MIL training,
  prediction, and experiment syncing through the FastAPI backend.
- Use Monte Carlo controls to prepare VM model-cache folders, generate random
  trial plans, bootstrap runners, rank stable-best models, and fetch uncertainty
  outputs.
- Show Hugging Face, Groq AI, Zerve AI, Firecrawl, and Tinyfish configured
  state without printing secret values.
- Keep VM/Jupyter commands visible and editable for the remote Slideflow flow.

The frontend does not invent model scores. It only reports values parsed from
the files you load in the browser.

## Getting Started

Run the development server:

```bash
npm.cmd run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

The frontend expects the FastAPI backend at:

```bash
NEXT_PUBLIC_MSI_API_URL=http://127.0.0.1:8001
```

If the variable is not set, the workstation defaults to
`http://127.0.0.1:8001`.

## VM Control

The frontend calls `src/app/api/vm/route.ts`, which runs SSH from the local
Next server. Your private key is used on the server side only, not inside
browser JavaScript.

Default connection:

```bash
ssh -i "%USERPROFILE%\.ssh\evolet_rsa" pardeep@34.55.157.128
```

Optional overrides:

```bash
MSI_VM_USER=pardeep
MSI_VM_HOST=34.55.157.128
MSI_VM_KEY=C:\Users\<you>\.ssh\evolet_rsa
MSI_VM_PROJECT_ROOT=/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
```

GUI actions:

- `Check VM` shows GPU, disk, slide counts, and running processes.
- `Browse project` lists allowed VM project folders.
- `Upload annotations` writes to `annotations/tcga_crc_msi_annotations.csv`.
- `Upload manifest` writes to `annotations/gdc_manifest_tcga_crc_msi.tsv`.
- `Start downloader` runs the GDC manifest downloader on the VM.
- `Start Jupyter` starts Jupyter on VM port `8888`.
- `Open tunnel` forwards local `http://127.0.0.1:8888` to the VM Jupyter port.
- `Prep VM cache` in the Monte Carlo approach creates Hugging Face and Monte
  Carlo model folders on the VM through the backend route
  `/vm/monte-carlo/workspace`.

## Approach Modes

- `Approach 1`: cohort/manifest validation, VM browsing, file upload,
  downloader, Jupyter, tunnel, experiment result, and tech surface.
- `Approach 2`: mounted platform workflow using `/approach-2/pipeline/*` and
  `/approach-2/experiments/*`.
- `Monte Carlo`: dedicated random-search and uncertainty workflow using
  `/experiments/monte-carlo-plan`, `/experiments/best-stable`, and VM model
  cache preparation.

## Expected Files

Annotation file:

- patient or case id column
- slide or filename column
- MSI label column, such as MSI-H or MSS
- fold or split column

Manifest file:

- GDC file id / UUID column
- diagnostic slide filename column

## Scripts

```bash
npm.cmd run lint
npm.cmd run build
```

## Project Shape

- `src/app/page.tsx` renders the workstation.
- `src/app/api/vm/route.ts` contains the local SSH bridge for VM actions.
- `src/components/msi-workbench.tsx` contains the upload parser, field mapping,
  validation, distributions, three-approach switch, VM controls, Approach 2
  controls, Monte Carlo controls, and command block.
- `src/app/globals.css` keeps the global theme small and app-focused.

## Safety Note

The VM bridge is designed for local development. It uses your local SSH key from
the server-side route and should not be deployed publicly without adding
authentication and secret management.
