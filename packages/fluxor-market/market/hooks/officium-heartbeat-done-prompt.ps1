# promptSubmit -- stops the heartbeat ticker of a background shell call once the call has ended: the
# PowerShell twin of officium-heartbeat-done-prompt.sh. Claude Code tells the agent that a
# background command finished with a prompt carrying a <task-notification> per task, each with the
# <tool-use-id> of the call whose ticker officium-heartbeat-done left running. Sends nothing.

$ErrorActionPreference = 'SilentlyContinue'
$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
$prompt = [string]$payload.prompt
if (-not $prompt.Contains('<task-notification>')) { exit 0 }
$session = [string]$payload.session_id
if ($session -notmatch '^[A-Za-z0-9_-]{1,128}$') { $session = 'none' }

$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path $(if ($env:HOME) { $env:HOME } else { $HOME }) '.cache' }
foreach ($m in [regex]::Matches($prompt, '<tool-use-id>([A-Za-z0-9_-]{1,128})</tool-use-id>')) {
  $ticker = Join-Path $root "officium/heartbeat/$session.$($m.Groups[1].Value).tick"
  if (-not (Test-Path -LiteralPath $ticker -PathType Leaf)) { continue }
  $id = [string](Get-Content -LiteralPath $ticker -TotalCount 1)
  Remove-Item -LiteralPath $ticker -Force
  if ($id -match '^\d+$') { Stop-Process -Id ([int]$id) -Force }
}
exit 0
