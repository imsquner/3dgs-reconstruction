param([switch]$NoBrowser,[switch]$Campus)
$ErrorActionPreference = 'Stop'
$demoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$demoUrl = 'http://127.0.0.1:8765'
$demoHealthy = $false
try { $demoResponse = Invoke-RestMethod "$demoUrl/health" -TimeoutSec 2; $demoHealthy = $demoResponse.app -eq '3dgs-course-interactive' } catch {}
if ($Campus -and $demoHealthy) {
    & (Join-Path $demoDir 'stop.ps1')
    $demoHealthy = $false
}
if (-not $demoHealthy) {
    $demoPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) { $demoPython = (Get-Command python -ErrorAction Stop).Source }
    $demoLogs = Join-Path $demoDir 'logs'
    New-Item -ItemType Directory -Force -Path $demoLogs | Out-Null
    $demoServer = Join-Path $demoDir 'server.py'
    $demoBind = if ($Campus) { '0.0.0.0' } else { '127.0.0.1' }
    $demoProcess = Start-Process -FilePath $demoPython -ArgumentList @('-u', ('"' + $demoServer + '"'), '--host', $demoBind) -WorkingDirectory $demoDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $demoLogs 'server.log') -RedirectStandardError (Join-Path $demoLogs 'server-error.log') -PassThru
    $demoProcess.Id | Set-Content -LiteralPath (Join-Path $demoLogs 'server.pid')
    for ($demoWait = 0; $demoWait -lt 20; $demoWait++) {
        Start-Sleep -Milliseconds 200
        try { $demoResponse = Invoke-RestMethod "$demoUrl/health" -TimeoutSec 1; if ($demoResponse.app -eq '3dgs-course-interactive') {$demoHealthy = $true; break} } catch {}
        if ($demoProcess.HasExited) { break }
    }
    if (-not $demoHealthy) { throw 'Demo service failed. Check logs or whether port 8765 is in use.' }
}
if (-not $NoBrowser) { Start-Process $demoUrl }
