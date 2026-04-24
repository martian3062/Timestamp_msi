# Timestamp_msi

Timestamp_msi is a local-first MSI-H vs MSS colorectal WSI workstation for the
4basecare Approach 1 project. It combines a Next.js frontend, a local Node API
bridge, and an SSH-connected pathology VM so the whole slide workflow can be
controlled from a simple browser GUI instead of repeatedly typing SSH commands.

The current app focuses on the TCGA colorectal cancer MSI workflow:

- validate MSI annotation files in the browser
- validate GDC diagnostic slide manifests in the browser
- inspect label and fold balance before model work
- connect to the pathology VM over SSH through a local API route
- browse the remote project folder
- upload selected annotation and manifest files to the VM project
- start or inspect the GDC slide downloader
- start Jupyter on the VM
- open a local SSH tunnel to Jupyter

The frontend is intentionally honest: it does not invent model scores or fake
clinical outputs. It only displays values parsed from uploaded files or returned
by the live VM.

## Repository Layout

```text
Timestamp_msi/
  apps/
    api/
      app/
      storage/
      tests/
    web/
      src/
        app/
          api/vm/route.ts
          globals.css
          layout.tsx
          page.tsx
        components/
          msi-workbench.tsx
      public/
      package.json
      package-lock.json
      README.md
      tsconfig.json
  configs/
  .gitignore
  README.md
```

`apps/web` is the working application today. `apps/api` and `configs` are
reserved scaffold folders for later backend or experiment configuration work.

## What Was Used

Frontend stack:

- Next.js 16.2.4 with the App Router
- React 19.2.4
- TypeScript 5
- Tailwind CSS 4 through `@tailwindcss/postcss`
- Lucide React icons
- Local browser file parsing for CSV and TSV files

Local server bridge:

- Next.js Route Handler at `apps/web/src/app/api/vm/route.ts`
- Node.js `child_process` for SSH execution
- Windows OpenSSH using the existing private key path
- Fixed action allowlist instead of arbitrary shell execution from the browser

Remote pathology VM:

- SSH command shape:

```powershell
ssh -i "%USERPROFILE%\.ssh\evolet_rsa" pardeep@34.55.157.128
```

- Project root on the VM:

```text
/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
```

- Python/Jupyter wrapper used on the VM:

```text
pathology310-run
```

- Jupyter target:

```text
127.0.0.1:8888 on the VM, forwarded locally to http://127.0.0.1:8888
```

Dataset/workflow sources:

- TCGA-COAD/READ diagnostic whole-slide images from GDC
- MSI labels from cBioPortal study `coadread_tcga_pan_can_atlas_2018`
- GDC manifest-driven `.svs` download
- Patient-level fold validation for MSI-H vs MSS experiments

## Application Features

### Cohort File Validation

The GUI accepts an annotation CSV and a GDC manifest CSV/TSV.

Annotation detection looks for:

- patient / case / submitter id
- slide / filename / file / image
- MSI / label / class / status
- fold / split

Manifest detection looks for:

- id / UUID / file id
- filename / file / name

After upload, the app shows:

- selected filename
- parsed row count
- detected columns
- missing required mappings
- MSI label distribution
- fold distribution

### VM Control Panel

The GUI provides buttons for common VM work:

- `Check VM`: shows hostname, user, GPU, disk, slide count, partial download
  count, slide folder size, and Jupyter/downloader processes.
- `Browse project`: lists files and folders in allowed VM project locations.
- `Upload annotations`: writes the selected annotation file to
  `annotations/tcga_crc_msi_annotations.csv` on the VM.
- `Upload manifest`: writes the selected manifest to
  `annotations/gdc_manifest_tcga_crc_msi.tsv` on the VM.
- `Start downloader`: starts `scripts/download_gdc_manifest.py` through
  `pathology310-run` and writes output to `logs/gdc_download.log`.
- `Start Jupyter`: starts Jupyter Lab on VM port `8888` through
  `pathology310-run`.
- `Open tunnel`: opens the local SSH tunnel from `http://127.0.0.1:8888` to
  the VM Jupyter port.

### Safety Model

The browser never receives the private SSH key. The key stays on the local
machine and is used by the local Next.js API route only.

The API route does not expose a free-form command box. It supports only a small
set of fixed actions:

- `status`
- `listFiles`
- `uploadFile`
- `startDownloader`
- `startJupyter`
- `startTunnel`

Project browsing is restricted to the configured VM project roots. This keeps
the GUI useful without turning it into a remote shell exposed to the browser.

Important: this app is meant to run locally on your Windows machine. Do not
deploy the VM SSH bridge route to a public hosting platform unless it is first
reworked with proper authentication, authorization, auditing, and secret
management.

## Runtime Flow

1. Start the local Next.js app.
2. Open the GUI in the browser.
3. Upload annotation and manifest files locally.
4. Let the browser validate labels, folds, and required columns.
5. Use `Upload annotations` and `Upload manifest` to copy those files to the VM.
6. Use `Check VM` to confirm GPU, disk, slide count, and process status.
7. Use `Start downloader` if the GDC slide download is not complete.
8. Use `Start Jupyter` and `Open tunnel`.
9. Open `http://127.0.0.1:8888` for the VM Jupyter session.

## Local Setup

From the web app folder:

```powershell
cd apps\web
npm.cmd install
npm.cmd run dev
```

Then open:

```text
http://127.0.0.1:3000
```

The development server can also appear as `http://localhost:3000`.

## Validation Commands

Run these from `apps/web`:

```powershell
npm.cmd run lint
npm.cmd run build
```

Both were passing after the VM GUI integration.

## VM Environment Overrides

The API route has defaults for the current VM, but each setting can be
overridden through environment variables before starting Next.js:

```powershell
$env:MSI_VM_USER = "pardeep"
$env:MSI_VM_HOST = "34.55.157.128"
$env:MSI_VM_KEY = "$env:USERPROFILE\.ssh\evolet_rsa"
$env:MSI_VM_PROJECT_ROOT = "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc"
npm.cmd run dev
```

## Verified VM State

The live VM check through the app API confirmed:

- host: `wsi-tca-experiments-3`
- GPU: NVIDIA L4
- slide folder: `slideflow_project/data/slides`
- completed slides: `60 .svs`
- partial downloads: `0 .part`
- slide storage used: about `34G`
- local Jupyter tunnel: `http://127.0.0.1:8888`

These values are runtime state, so the GUI should be used as the source of
truth whenever you resume work.

## Development Notes

Main files:

- `apps/web/src/components/msi-workbench.tsx`: browser UI, file parsing,
  cohort validation, VM action buttons, and output panels.
- `apps/web/src/app/api/vm/route.ts`: Node.js SSH bridge and fixed VM actions.
- `apps/web/src/app/page.tsx`: renders the workstation.
- `apps/web/src/app/layout.tsx`: metadata and app shell.
- `apps/web/src/app/globals.css`: global theme and base styling.
- `apps/web/README.md`: frontend-specific operating notes.

## GitHub Publish Commands

The repository target requested for this project is:

```text
https://github.com/martian3062/Timestamp_msi.git
```

Initial publish flow:

```powershell
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/martian3062/Timestamp_msi.git
git push -u origin main
```
