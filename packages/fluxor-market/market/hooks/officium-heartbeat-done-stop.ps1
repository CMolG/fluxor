# stop -- the safety net behind officium-heartbeat-done-prompt, the PowerShell twin of
# officium-heartbeat-done-stop.sh: when a turn ends, every background ticker of the session whose task
# the payload's `background_tasks` no longer lists as running is stopped. A client whose stop payload
# has no `background_tasks` is left alone: the ticker's own ceiling ends it. An entry with no status
# is taken as running. Sends nothing.

$ErrorActionPreference = 'SilentlyContinue'
$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
if (-not $payload -or -not $payload.PSObject.Properties['background_tasks']) { exit 0 }
$session = [string]$payload.session_id
if ($session -notmatch '^[A-Za-z0-9_-]{1,128}$') { $session = 'none' }

$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path $(if ($env:HOME) { $env:HOME } else { $HOME }) '.cache' }
$state = Join-Path $root 'officium/heartbeat'
if (-not (Test-Path -LiteralPath $state -PathType Container)) { exit 0 }
$tasks = @($payload.background_tasks)
foreach ($file in Get-ChildItem -LiteralPath $state -Filter "$session.*.tick") {
  $lines = @(Get-Content -LiteralPath $file.FullName)
  if ($lines.Count -lt 2 -or $lines[1] -notmatch '^[A-Za-z0-9_-]{1,128}$') { continue }   # a foreground call's ticker
  $entry = $tasks | Where-Object { $_.id -eq $lines[1] } | Select-Object -First 1
  if ($entry -and (-not $entry.status -or $entry.status -eq 'running')) { continue }
  Remove-Item -LiteralPath $file.FullName -Force
  if ($lines[0] -match '^\d+$') { Stop-Process -Id ([int]$lines[0]) -Force }
}
exit 0
