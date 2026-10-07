param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dataPath = Join-Path $projectRoot '_data'
New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
$url = 'http://127.0.0.1:8012'
$existing = Get-NetTCPConnection -State Listen -LocalPort 8012 -ErrorAction SilentlyContinue
if (-not $existing) {
    $process = Start-Process -FilePath $pythonPath -ArgumentList @(
        '-m', 'uvicorn', 'printready.api:app', '--host', '127.0.0.1', '--port', '8012'
    ) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $dataPath 'server.stdout.log') `
      -RedirectStandardError (Join-Path $dataPath 'server.stderr.log')
    Write-Output "Started PrintReady process $($process.Id)"
}
$ready = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
        if ($response.status -eq 'ok' -and $response.physical_controls -eq $false) {
            $ready = $true
            break
        }
    } catch { }
    Start-Sleep -Milliseconds 250
}
if (-not $ready) { throw 'PrintReady did not become healthy. Check _data/server.stderr.log.' }
Write-Output "PrintReady ready at $url"
if (-not $NoBrowser) { Start-Process $url }
