# One command to get this repo working on a fresh Windows install. Safe to rerun.
#
#     .\setup.ps1
#
# Uses your conda/miniconda Python (or installs Python 3.12 with winget if there's none), makes .venv from it,
# installs requirements.txt, starts the `leetpg` Postgres container (creating it if needed), and seeds the
# `practice` database.
# Native commands report failure through $LASTEXITCODE, so this checks it after each step.

$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "`n$msg" -ForegroundColor Red; exit 1 }

function Find-Python {
    # An active conda env first (your miniconda base), then the usual install folders.
    $dirs = @($env:CONDA_PREFIX, "$env:USERPROFILE\miniconda3", "$env:LOCALAPPDATA\miniconda3",
              "C:\ProgramData\miniconda3", "$env:USERPROFILE\anaconda3",
              "$env:LOCALAPPDATA\Programs\Python\Python312", "$env:LOCALAPPDATA\Programs\Python\Python313")
    foreach ($d in $dirs) {
        if ($d -and (Test-Path "$d\python.exe")) { return "$d\python.exe" }
    }
    foreach ($name in 'python', 'python3') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        # The python.exe under WindowsApps is the Microsoft Store stub, not a real interpreter.
        if ($cmd -and $cmd.Source -notlike '*\WindowsApps\*') { return $cmd.Source }
    }
    return $null
}

$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    Step 'Python'
    $py = Find-Python
    if (-not $py) {
        Write-Host 'Installing Python 3.12 for your user account with winget...'
        winget install --exact --id Python.Python.3.12 --scope user --source winget
        $py = Find-Python
        if (-not $py) { Fail 'Python still not found. Install 3.12 from python.org, then rerun .\setup.ps1' }
    }
    Write-Host "Using $py"
    & $py -m venv .venv
    if ($LASTEXITCODE) { Fail 'Could not create .venv (see above).' }
}

Step 'Python packages'
& $venvPy -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE) { Fail 'pip install failed (see above).' }

Step 'Postgres (Docker container leetpg)'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail 'Docker is not installed. Install Docker Desktop, start it, then rerun .\setup.ps1'
}
cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE) { Fail 'Docker Desktop is not running. Start it, wait until it says "Engine running", then rerun .\setup.ps1' }
$existing = docker ps -a --filter 'name=^leetpg$' --format '{{.Names}}'
if ($existing -eq 'leetpg') {
    docker start leetpg | Out-Null
} else {
    # The named volume keeps the data if the container is ever removed.
    docker run -d --name leetpg --restart unless-stopped -e POSTGRES_PASSWORD=leet -p 5432:5432 `
        -v leetpg-data:/var/lib/postgresql/data postgres:16 | Out-Null
}
if ($LASTEXITCODE) { Fail 'Could not start the leetpg container (see above). Is something else using port 5432?' }
$ready = $false
foreach ($i in 1..60) {
    # Over TCP on purpose: during first-time init Postgres only listens on a socket, then restarts.
    cmd /c "docker exec leetpg pg_isready -h 127.0.0.1 -U postgres -q >nul 2>&1"
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Fail 'Postgres did not come up within a minute. Check: docker logs leetpg' }

Step 'practice database (about 40 s the first time)'
& $venvPy tasks.py setup-db --if-missing
if ($LASTEXITCODE) { Fail 'Seeding failed (see above).' }

& $venvPy tasks.py done setup | Out-Null
Write-Host "`nREADY." -ForegroundColor Green
Write-Host 'Next: python tasks.py next   (any terminal, no activation: tasks.py switches to .venv by itself)'
