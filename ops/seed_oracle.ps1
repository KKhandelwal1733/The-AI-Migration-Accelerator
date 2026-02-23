$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sqlFile = Join-Path $scriptDir "seed_oracle.sql"

Get-Content -Raw $sqlFile | podman compose -f (Join-Path $scriptDir "podman-compose.yml") exec -T oracle sqlplus accelerator/accelerator@localhost:1521/XEPDB1 @/dev/stdin

Write-Host "Oracle demo schema/data seeded successfully."
