param(
  [string]$VmUser = "pardeep",
  [string]$VmHost = "34.59.145.240",
  [string]$VmKey = "$env:USERPROFILE\.ssh\evolet_rsa",
  [string]$VmProjectRoot = "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$mirrorRoot = Join-Path $scriptRoot "current"

if (Test-Path $mirrorRoot) {
  Remove-Item -LiteralPath $mirrorRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $mirrorRoot | Out-Null

$remoteFind = @"
cd '$VmProjectRoot'
find automation/logs -maxdepth 1 -type f 2>/dev/null
find output/triad_runs -maxdepth 2 -type f \( -name 'metrics.json' -o -name 'status.json' -o -name 'run.log' \) 2>/dev/null
"@

$files = @(
  & ssh -i $VmKey "$VmUser@$VmHost" $remoteFind |
    Where-Object { $_ -and $_.Trim() -ne "" } |
    Sort-Object -Unique
)

foreach ($relativePath in $files) {
  $localPath = Join-Path $mirrorRoot ($relativePath -replace "/", "\")
  $localDir = Split-Path -Parent $localPath
  New-Item -ItemType Directory -Force -Path $localDir | Out-Null
  & scp -i $VmKey "$VmUser@$VmHost`:$VmProjectRoot/$relativePath" $localPath | Out-Null
}

Write-Host "VM logs mirrored into $mirrorRoot"
