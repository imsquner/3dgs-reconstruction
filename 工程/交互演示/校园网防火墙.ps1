param([switch]$Remove)
$ErrorActionPreference='Stop'
$demoAdmin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $demoAdmin) { throw 'Run this script in an Administrator PowerShell window.' }
$demoRule='3DGS-Course-Campus-8765'
if ($Remove) { Get-NetFirewallRule -Name $demoRule -ErrorAction SilentlyContinue | Remove-NetFirewallRule; exit }
$demoPython=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Bundled Python not found.' }
if (-not (Get-NetFirewallRule -Name $demoRule -ErrorAction SilentlyContinue)) {
 New-NetFirewallRule -Name $demoRule -DisplayName '3DGS course campus demo' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Program $demoPython -Profile Any -InterfaceAlias WLAN -RemoteAddress 10.0.0.0/8
}
Get-NetFirewallRule -Name $demoRule | Select-Object Name,Enabled,Action
