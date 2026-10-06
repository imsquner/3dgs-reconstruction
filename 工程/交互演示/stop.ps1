$ErrorActionPreference = 'Stop'
$demoResponse = Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2
if ($demoResponse.app -ne '3dgs-course-interactive') { throw 'Not our demo service; will not stop it.' }
Invoke-WebRequest 'http://127.0.0.1:8765/shutdown' -Method Post -UseBasicParsing | Out-Null
for ($demoWait = 0; $demoWait -lt 25; $demoWait++) {
    Start-Sleep -Milliseconds 200
    try { Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 1 | Out-Null } catch { Write-Output 'Demo service stopped.'; exit 0 }
}
throw 'Shutdown requested, but port 8765 still responds.'
