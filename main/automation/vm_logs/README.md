# VM Logs Mirror

This folder stores a local copy of selected logs and metric snapshots from the
GPU VM:

- `automation/logs/*`
- `output/triad_runs/*/run.log`
- `output/triad_runs/*/metrics.json`
- `output/triad_runs/*/status.json`
- `output/triad_runs/run.log`

Use [sync-vm-logs.ps1](</e:/4basecare-MSI/main/automation/vm_logs/sync-vm-logs.ps1>)
to refresh this mirror from:

- host: `34.59.145.240`
- user: `pardeep`
- key: `%USERPROFILE%\.ssh\evolet_rsa`

The sync is non-destructive for the VM. It only copies files down into this
repo.
