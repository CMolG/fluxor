# Clears what officium-attention marked: once a tool runs, the person types, or the turn ends, nothing
# waits on them any more. One script, shipped as three hooks (officium-attention-clear-tool, -prompt,
# -stop), one per event; the PowerShell twin of officium-attention-clear-tool.sh. Only a window that
# marked itself speaks. Token, API and the autonomous-loop switches as officium-attention; the request
# runs in a detached process, and the token stays inside it.
#
#   officium-attention-clear-*.ps1                  the hook (stdin: the client's JSON)
#   officium-attention-clear-*.ps1 put <session>    the detached request

param([string]$Mode = '', [string]$Session = '')
$ErrorActionPreference = 'SilentlyContinue'

function Get-HomeDir { if ($env:HOME) { return $env:HOME } return $HOME }

if ($Mode -eq 'put') {
  if ($Session -notmatch '^[A-Za-z0-9_-]{1,128}$') { exit 0 }
  $token = [string]$env:OFFICIUM_HEARTBEAT_TOKEN
  if (-not $token) {
    $file = $env:OFFICIUM_HEARTBEAT_TOKEN_FILE
    if (-not $file) { $file = Join-Path (Get-HomeDir) '.config/officium/heartbeat-token' }
    if (Test-Path -LiteralPath $file -PathType Leaf) { $token = [string](Get-Content -LiteralPath $file -TotalCount 1) }
  }
  $token = $token -replace '\s', ''
  if (-not $token) { exit 0 }
  $api = [string]$env:OFFICIUM_API_URL
  if (-not $api) { $api = '{{OFFICIUM_API}}' }
  if ($api.StartsWith('{{')) { $api = 'https://javadaba.com/api' }   # installed without the param
  Invoke-WebRequest -UseBasicParsing -Method Put -Uri "$($api.TrimEnd('/'))/officium/v1/sessions/$Session/attention" -TimeoutSec 3 `
    -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes('{"blocked":false}')) | Out-Null
  exit 0
}

if ($env:AUTOLOOP_SLOT -or $env:OFFICIUM_SESSIONS -eq '0') { exit 0 }
$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
$session = [string]$payload.session_id
if ($session -notmatch '^[A-Za-z0-9_-]{1,128}$') { exit 0 }
$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path (Get-HomeDir) '.cache' }
$marker = Join-Path $root "officium/attention/$session.blocked"
if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) { exit 0 }
Remove-Item -LiteralPath $marker -Force

$arguments = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", 'put', $session)
$exe = (Get-Process -Id $PID).Path
if ($env:OS -eq 'Windows_NT') { [void](Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden) }
else {
  # Off Windows, Start-Process refuses one file for both streams, so it started nothing (JAVA-760):
  # every stream is a pipe instead, so the hook returns at once and the child outlives it.
  $psi = [System.Diagnostics.ProcessStartInfo]::new($exe)
  foreach ($a in $arguments) { $psi.ArgumentList.Add($a.Trim('"')) }
  $psi.RedirectStandardInput = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
  [void][System.Diagnostics.Process]::Start($psi)
}
exit 0
