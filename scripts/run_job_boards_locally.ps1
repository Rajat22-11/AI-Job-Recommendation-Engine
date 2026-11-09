# Run only the job-board sources (Indeed, Naukri, Glassdoor via JobSpy) from this PC, whose home IP is
# less likely to be blocked than a cloud server's. Results go to the same database without duplicates.
#
# Secrets are read from a local, git-ignored file: <repo>\.env.local with lines NAME=value, at least
# SUPABASE_URL and SUPABASE_SERVICE_KEY (NTFY_TOPIC optional). Never commit that file.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\run_job_boards_locally.ps1 [-DryRun]

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repo ".env.local"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("job-boards-" + (Get-Date -Format "yyyy-MM-dd") + ".log")

if (-not (Test-Path $envFile)) { throw "Missing $envFile (see docs/deployment.md)" }
# The program itself reads .env.local (same variable names as Render); nothing to parse here.

$arguments = @("-m", "job_aggregator.orchestration.run_daily", "--only-methods", "jobspy_board",
               "--trigger-id", "pc-task-scheduler", "--config-dir", (Join-Path $repo "config"))
if ($DryRun) { $arguments += "--dry-run" }

Push-Location $repo
try {
    & $python @arguments *>> $log
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
Write-Output "job boards run finished with exit code $code (log: $log)"
exit $code
