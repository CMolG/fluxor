# preTool (every tool) -- Officium heartbeat, the PowerShell twin of officium-heartbeat.sh: keeps the
# card an agent works lit on Officium's board, at zero model tokens.
#
# One status line from the tool call, at most one per OFFICIUM_HEARTBEAT_INTERVAL seconds (default
# 10); a shell call also starts a ticker that re-beats "<description>, 3m12s" every
# OFFICIUM_HEARTBEAT_TICK seconds (default 30) until officium-heartbeat-done stops it, and that gives
# up on its own after 11 minutes, or within one tick once CLAUDE_PID (its client) is gone. A call that goes to the background keeps its ticker past its
# postTool, which records the task id in the ticker's file, for up to OFFICIUM_HEARTBEAT_BG_MAX
# seconds (default 7200), until officium-heartbeat-done-prompt (the task's notification) or
# officium-heartbeat-done-stop (a turn ending with the task no longer running) stops it. Each beat
# carries the model and effort of the transcript's last assistant line. Installing it is the opt-in;
# with no token it says so once per session and sends nothing. Token: OFFICIUM_HEARTBEAT_TOKEN, or
# the file OFFICIUM_HEARTBEAT_TOKEN_FILE (default ~/.config/officium/heartbeat-token). Machine:
# OFFICIUM_MACHINE, else COMPUTERNAME, else the host name. API: OFFICIUM_API_URL, else
# {{OFFICIUM_API}}. The request runs in a detached process, so it never holds a tool; the token stays
# inside the process, never on a command line.
#
#   officium-heartbeat.ps1                               the hook (stdin: the client's JSON)
#   officium-heartbeat.ps1 send <session> <b64 text> <b64 transcript>   one detached beat
#   officium-heartbeat.ps1 tick <session> <call> <b64 text> <b64 transcript>   the long-call ticker

param([string]$Mode = '', [string]$Session = '', [string]$Arg1 = '', [string]$Arg2 = '', [string]$Arg3 = '')
$ErrorActionPreference = 'SilentlyContinue'

function Read-Token {
  $t = [string]$env:OFFICIUM_HEARTBEAT_TOKEN
  if (-not $t) {
    $file = $env:OFFICIUM_HEARTBEAT_TOKEN_FILE
    if (-not $file) { $file = Join-Path (Get-HomeDir) '.config/officium/heartbeat-token' }
    if (Test-Path -LiteralPath $file -PathType Leaf) { $t = [string](Get-Content -LiteralPath $file -TotalCount 1) }
  }
  return ($t -replace '\s', '')
}
function Get-HomeDir { if ($env:HOME) { return $env:HOME } return $HOME }
function Get-StateDir([string]$Name) {
  $root = $env:XDG_RUNTIME_DIR
  if (-not $root) { $root = Join-Path (Get-HomeDir) '.cache' }
  $dir = Join-Path (Join-Path $root 'officium') $Name
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
    if ($env:OS -eq 'Windows_NT') { [void](New-Item -ItemType Directory -Force -Path $dir) }
    else { [void][System.IO.Directory]::CreateDirectory($dir, [System.IO.UnixFileMode]'UserRead, UserWrite, UserExecute') }
  }
  if (Test-Path -LiteralPath $dir -PathType Container) { return $dir }
  return $null
}
function Get-Api {
  $api = [string]$env:OFFICIUM_API_URL
  if (-not $api) { $api = '{{OFFICIUM_API}}' }
  if ($api.StartsWith('{{')) { $api = 'https://javadaba.com/api' }   # installed without the param
  return $api.TrimEnd('/')
}
function Start-Detached([string[]]$Arguments) {
  $quoted = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"") + $Arguments
  $exe = (Get-Process -Id $PID).Path
  if ($env:OS -eq 'Windows_NT') { return Start-Process -FilePath $exe -ArgumentList $quoted -WindowStyle Hidden -PassThru }
  # Off Windows, Start-Process refuses one file for both streams, so it started nothing (JAVA-760):
  # every stream is a pipe instead, so the hook returns at once and the child outlives it.
  $psi = [System.Diagnostics.ProcessStartInfo]::new($exe)
  foreach ($a in $quoted) { $psi.ArgumentList.Add($a.Trim('"')) }
  $psi.RedirectStandardInput = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
  return [System.Diagnostics.Process]::Start($psi)
}
# Start-Process drops an empty argument, which would shift the rest, and Windows PowerShell reads a
# bare '-' as a parameter: an empty string travels as '_', which base64 never produces.
function To-B64([string]$s) { if (-not $s) { return '_' } [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($s)) }
function From-B64([string]$s) { if (-not $s -or $s -eq '_') { return '' } [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($s)) }

# The model and effort of the transcript's last assistant line: only a `"model":"` or `"effort":"`
# with bare quotes matches, since inside a string their quotes are escaped.
function Get-RunsOn([string]$Transcript) {
  $found = @{}
  if (-not $Transcript -or -not (Test-Path -LiteralPath $Transcript -PathType Leaf)) { return $found }
  $stream = [System.IO.File]::Open($Transcript, 'Open', 'Read', 'ReadWrite')
  try {
    $length = [Math]::Min($stream.Length, 262144)
    [void]$stream.Seek(-$length, 'End')
    $bytes = New-Object byte[] $length
    [void]$stream.Read($bytes, 0, $length)
  } finally { $stream.Close() }
  $text = [Text.Encoding]::UTF8.GetString($bytes)
  foreach ($m in [regex]::Matches($text, '"(model|effort)":"([A-Za-z0-9._-]{1,100})"')) { $found[$m.Groups[1].Value] = $m.Groups[2].Value }
  return $found
}

function Send-Beat([string]$Text, [string]$Transcript) {
  $token = Read-Token
  $machine = $env:OFFICIUM_MACHINE
  if (-not $machine) { $machine = $env:COMPUTERNAME }
  if (-not $machine) { $machine = [System.Net.Dns]::GetHostName() }
  $body = [ordered]@{ machine = ($machine -replace '["\\]', ''); text = $Text }
  $runsOn = Get-RunsOn $Transcript
  if ($runsOn['model']) { $body.model = $runsOn['model'] }
  if ($runsOn['effort']) { $body.effort = $runsOn['effort'].Substring(0, [Math]::Min(20, $runsOn['effort'].Length)) }
  $json = $body | ConvertTo-Json -Compress
  Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$(Get-Api)/officium/v1/heartbeat" -TimeoutSec 2 `
    -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes($json)) | Out-Null
}

# One beat per interval per session: the first process to create this slot's file sends.
function Invoke-Beat([string]$State, [string]$Sess, [string]$Text, [string]$Transcript) {
  $interval = [int]$env:OFFICIUM_HEARTBEAT_INTERVAL
  if ($interval -le 0) { $interval = 10 }
  $slot = [Math]::Floor([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() / $interval)
  $mark = Join-Path $State "$Sess.$slot.slot"
  try { ([System.IO.File]::Open($mark, 'CreateNew')).Close() } catch { return }
  Get-ChildItem -LiteralPath $State -Filter "$Sess.*.slot" | Where-Object { $_.FullName -ne $mark } | Remove-Item -Force
  if ($env:OFFICIUM_HEARTBEAT_SYNC -eq '1') { Send-Beat $Text $Transcript }
  else { [void](Start-Detached @('send', $Sess, (To-B64 $Text), (To-B64 $Transcript))) }
}

if ($Mode -eq 'send') { Send-Beat (From-B64 $Arg1) (From-B64 $Arg2); exit 0 }

$state = Get-StateDir 'heartbeat'
if (-not $state) { exit 0 }

if ($Mode -eq 'tick') {
  $call = $Arg1; $text = From-B64 $Arg2; $transcript = From-B64 $Arg3
  $ticker = Join-Path $state "$Session.$call.tick"
  $tick = [int]$env:OFFICIUM_HEARTBEAT_TICK
  if ($tick -le 0) { $tick = 30 }
  $bgMax = [int]$env:OFFICIUM_HEARTBEAT_BG_MAX
  if ($bgMax -le 0) { $bgMax = 7200 }
  $max = 660
  $started = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  while (Test-Path -LiteralPath $ticker) {
    Start-Sleep -Seconds $tick
    if (-not (Test-Path -LiteralPath $ticker)) { break }
    # The client process that started this call is gone (a recycled or killed session never runs a postTool): stop.
    if ($env:CLAUDE_PID -match '^[0-9]+$' -and -not (Get-Process -Id ([int]$env:CLAUDE_PID) -ErrorAction SilentlyContinue)) { break }
    # A second line is the task id officium-heartbeat-done wrote when the call went to the background.
    $lines = @(Get-Content -LiteralPath $ticker)
    if ($lines.Count -ge 2 -and $lines[1]) { $max = $bgMax }
    $elapsed = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $started
    if ($elapsed -ge $max) { break }
    Invoke-Beat $state $Session ('{0}, {1}m{2}s' -f $text, [Math]::Floor($elapsed / 60), ($elapsed % 60)) $transcript
  }
  Remove-Item -LiteralPath $ticker -Force
  exit 0
}

$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
if (-not $payload) { exit 0 }
$session = ([string]$payload.session_id) -replace '[^A-Za-z0-9_-]', ''
if (-not $session) { $session = 'none' }

$token = Read-Token
if (-not $token) {
  # The marker officium-usage checks too, so a session hears it once, from whichever hook runs first.
  try {
    ([System.IO.File]::Open((Join-Path $state "$session.notoken"), 'CreateNew')).Close()
    Write-Output '{"systemMessage":"Officium heartbeat is installed but has no token: the card can lapse and no time gets reported. Create one in Officium (Connect an agent) and save it to ~/.config/officium/heartbeat-token, or set OFFICIUM_HEARTBEAT_TOKEN."}'
  } catch { }
  exit 0
}

$tool = [string]$payload.tool_name
if (-not $tool -or $tool.StartsWith('mcp__officium__')) { exit 0 }   # its own MCP writes already renew the card
$inputs = $payload.tool_input
$description = [string]$inputs.description
$file = [string]$inputs.file_path
if (-not $file) { $file = [string]$inputs.notebook_path }
$file = ($file -split '[/\\]')[-1]
$shell = @('Bash', 'PowerShell', 'shell', 'exec_command') -contains $tool
switch -Regex ($tool) {
  '^(Bash|PowerShell|shell|exec_command)$' { $text = if ($description) { $description } else { 'Running a command' }; break }
  '^(Edit|MultiEdit|Write|NotebookEdit|apply_patch)$' { $text = if ($file) { "Editing $file" } else { 'Editing files' }; break }
  '^Read$' { $text = "Reading $file"; break }
  '^(Grep|Glob)$' { $text = 'Searching the code'; break }
  '^(Agent|Task)$' { $text = if ($description) { "Delegating: $description" } else { 'Delegating: a subtask' }; break }
  '^(WebFetch|WebSearch)$' { $text = 'Researching on the web'; break }
  default { $text = "Using $tool" }
}
if ($text.Length -gt 200) { $text = $text.Substring(0, 200) }
$transcript = [string]$payload.transcript_path

Invoke-Beat $state $session $text $transcript

$call = ([string]$payload.tool_use_id) -replace '[^A-Za-z0-9_-]', ''
if (-not $shell -or -not $call) { exit 0 }
$ticker = Join-Path $state "$session.$call.tick"
Set-Content -LiteralPath $ticker -Value '' -NoNewline
$child = Start-Detached @('tick', $session, $call, (To-B64 $text), (To-B64 $transcript))
if ($child) { Set-Content -LiteralPath $ticker -Value $child.Id }
exit 0
