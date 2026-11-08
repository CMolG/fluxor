# postToolFailure (every tool) -- the failed or interrupted twin of officium-heartbeat-done. Claude
# Code fires PostToolUseFailure, never PostToolUse, for a call that fails, so this stops the ticker
# then. A failed call carries no tool_response and starts no background task. Sends nothing. The
# PowerShell twin of officium-heartbeat-done-failure.sh.

$ErrorActionPreference = 'SilentlyContinue'
$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
if (-not $payload) { exit 0 }
$session = [string]$payload.session_id
$call = [string]$payload.tool_use_id
if ($session -notmatch '^[A-Za-z0-9_-]{1,128}$') { $session = 'none' }
if ($call -notmatch '^[A-Za-z0-9_-]{1,128}$') { exit 0 }

$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path $(if ($env:HOME) { $env:HOME } else { $HOME }) '.cache' }
$ticker = Join-Path $root "officium/heartbeat/$session.$call.tick"
if (-not (Test-Path -LiteralPath $ticker -PathType Leaf)) { exit 0 }
$task = [string]$payload.tool_response.backgroundTaskId
if ($task -match '^[A-Za-z0-9_-]{1,128}$') {
  Add-Content -LiteralPath $ticker -Value $task
  exit 0
}
$id = [string](Get-Content -LiteralPath $ticker -TotalCount 1)
Remove-Item -LiteralPath $ticker -Force
if ($id -match '^\d+$') { Stop-Process -Id ([int]$id) -Force }
exit 0
