# notification (permission prompt, MCP question) -- tells Officium's board this agent window waits on
# its person. The PowerShell twin of officium-attention.sh, which explains the design: it marks the
# window blocked, the officium-attention-clear hooks clear it. Silent with no token, for any other
# notification, for an odd session id, and in an autonomous loop (AUTOLOOP_SLOT set, or
# OFFICIUM_SESSIONS=0). The request runs in a detached process; the token stays inside it.
#
#   officium-attention.ps1                         the hook (stdin: the client's JSON)
#   officium-attention.ps1 put <session> <reason>  the detached request

param([string]$Mode = '', [string]$Session = '', [string]$Reason = '')
$ErrorActionPreference = 'SilentlyContinue'

function Get-HomeDir { if ($env:HOME) { return $env:HOME } return $HOME }
function Read-Token {
  $t = [string]$env:OFFICIUM_HEARTBEAT_TOKEN
  if (-not $t) {
    $file = $env:OFFICIUM_HEARTBEAT_TOKEN_FILE
    if (-not $file) { $file = Join-Path (Get-HomeDir) '.config/officium/heartbeat-token' }
    if (Test-Path -LiteralPath $file -PathType Leaf) { $t = [string](Get-Content -LiteralPath $file -TotalCount 1) }
  }
  return ($t -replace '\s', '')
}

if ($Mode -eq 'put') {
  if ($Session -notmatch '^[A-Za-z0-9_-]{1,128}$' -or $Reason -notmatch '^(permission_prompt|elicitation_dialog)$') { exit 0 }
  $api = [string]$env:OFFICIUM_API_URL
  if (-not $api) { $api = '{{OFFICIUM_API}}' }
  if ($api.StartsWith('{{')) { $api = 'https://javadaba.com/api' }   # installed without the param
  $json = [ordered]@{ blocked = $true; reason = $Reason } | ConvertTo-Json -Compress
  Invoke-WebRequest -UseBasicParsing -Method Put -Uri "$($api.TrimEnd('/'))/officium/v1/sessions/$Session/attention" -TimeoutSec 3 `
    -Headers @{ Authorization = "Bearer $(Read-Token)" } -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes($json)) | Out-Null
  exit 0
}

if ($env:AUTOLOOP_SLOT -or $env:OFFICIUM_SESSIONS -eq '0') { exit 0 }
$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
$session = [string]$payload.session_id
$reason = [string]$payload.notification_type
if ($session -notmatch '^[A-Za-z0-9_-]{1,128}$' -or $reason -notmatch '^(permission_prompt|elicitation_dialog)$') { exit 0 }
if (-not (Read-Token)) { exit 0 }

$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path (Get-HomeDir) '.cache' }
$state = Join-Path $root 'officium/attention'
if (-not (Test-Path -LiteralPath $state)) {
  if ($env:OS -eq 'Windows_NT') { [void](New-Item -ItemType Directory -Force -Path $state) }
  else { [void][System.IO.Directory]::CreateDirectory($state, [System.IO.UnixFileMode]'UserRead, UserWrite, UserExecute') }
}
Set-Content -LiteralPath (Join-Path $state "$session.blocked") -Value ''

$arguments = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", 'put', $session, $reason)
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
