# sessionStart -- makes this window an Officium agent window, so cards can be queued into it from the
# board. Also its waiter: `officium-session.ps1 wait <session_id>`. The PowerShell twin of
# officium-session.sh, which explains the design; in short:
#
# The hook registers the window with Officium and tells the agent to start this same script in wait
# mode, in the background. The waiter long-polls Officium and finishes when someone queues a card into
# this window, printing ONE line: `OFFICIUM_CARD <KEY> <projectId>`, `OFFICIUM_WAIT_AGAIN` (only
# with OFFICIUM_WAIT_MAX set), `OFFICIUM_WAITER_REPLACED`, `OFFICIUM_WAITER_STOPPED <session>` or
# `OFFICIUM_WAIT_FAILED <reason>`. It prints a card key that matched a strict pattern and a UUID,
# never anything else the server sent, and confirms a card before printing it. It never finishes
# just because time passed, and sessionStart stops the waiters a /clear left behind (JAVA-963).
#
# The hook says nothing with no token, no network, a waiter this process runs, or in an autonomous loop
# (AUTOLOOP_SLOT set, or OFFICIUM_SESSIONS=0). Token, machine, API, label, OFFICIUM_WAIT_MAX and
# OFFICIUM_WAIT_POLL as officium-session.sh. The token stays inside the process.

param([string]$Mode = '', [string]$Session = '')
$ErrorActionPreference = 'SilentlyContinue'

function Get-HomeDir { if ($env:HOME) { return $env:HOME } return $HOME }
$token = [string]$env:OFFICIUM_HEARTBEAT_TOKEN
$tokenFile = $env:OFFICIUM_HEARTBEAT_TOKEN_FILE
if (-not $tokenFile) { $tokenFile = Join-Path (Get-HomeDir) '.config/officium/heartbeat-token' }
if (-not $token -and (Test-Path -LiteralPath $tokenFile -PathType Leaf)) { $token = [string](Get-Content -LiteralPath $tokenFile -TotalCount 1) }
$token = $token -replace '\s', ''

$api = [string]$env:OFFICIUM_API_URL
if (-not $api) { $api = '{{OFFICIUM_API}}' }
if ($api.StartsWith('{{')) { $api = 'https://javadaba.com/api' }   # installed without the param
$api = $api.TrimEnd('/')
$machine = $env:OFFICIUM_MACHINE
if (-not $machine) { $machine = $env:COMPUTERNAME }
if (-not $machine) { $machine = [System.Net.Dns]::GetHostName() }
$label = $env:OFFICIUM_SESSION_LABEL
if (-not $label) { $label = Split-Path -Leaf (Get-Location).Path }
$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path (Get-HomeDir) '.cache' }
$state = Join-Path $root 'officium/wait'

# The HTTP status (0 when unreachable) and the answer's text.
function Invoke-Officium([string]$Method, [string]$Path, [string]$Json, [int]$Timeout) {
  $request = @{ UseBasicParsing = $true; Method = $Method; Uri = "$api$Path"; TimeoutSec = $Timeout
    Headers = @{ Authorization = "Bearer $token" } }
  if ($Json) { $request.ContentType = 'application/json; charset=utf-8'; $request.Body = [Text.Encoding]::UTF8.GetBytes($Json) }
  try {
    $r = Invoke-WebRequest @request
    $text = $r.Content
    if ($text -is [byte[]]) { $text = [Text.Encoding]::UTF8.GetString($text) }
    return @{ Code = [int]$r.StatusCode; Text = [string]$text }
  } catch {
    $response = $_.Exception.Response
    if ($response) { return @{ Code = [int]$response.StatusCode; Text = '' } }
    return @{ Code = 0; Text = '' }
  }
}
function Register([string]$Sess, [int]$Timeout) {
  $json = [ordered]@{ sessionId = $Sess; machine = ($machine -replace '["\\]', ''); label = ($label -replace '["\\]', '') } | ConvertTo-Json -Compress
  return (Invoke-Officium 'POST' '/officium/v1/sessions' $json $Timeout).Code
}

if ($Mode -ne 'wait') {
  if ($env:AUTOLOOP_SLOT -or $env:OFFICIUM_SESSIONS -eq '0' -or -not $token) { exit 0 }
  $payload = $null
  try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
  $sess = [string]$payload.session_id
  if ($sess -notmatch '^[A-Za-z0-9_-]{1,128}$') { exit 0 }
  $pidFile = Join-Path $state "$sess.pid"
  # A waiter file is "<pid>`n<CLAUDE_PID>". One this process runs for another session served the
  # window a /clear ended: marked "stopped", that waiter says so and finishes after its call in flight.
  if ($env:CLAUDE_PID -and (Test-Path -LiteralPath $state)) {
    foreach ($file in Get-ChildItem -LiteralPath $state -Filter '*.pid' -File) {
      if ($file.Name -eq "$sess.pid") { continue }
      $lines = @(Get-Content -LiteralPath $file.FullName -TotalCount 3)
      if ($lines.Count -lt 2 -or [string]$lines[1] -ne [string]$env:CLAUDE_PID) { continue }
      # A marker already "stopped" stays while its waiter lives (it has not read it yet), so a second
      # sessionStart cannot delete it and leave that waiter running unbounded.
      $id = [string]$lines[0]
      if ($id -eq 'stopped' -and $lines.Count -ge 3) { $id = [string]$lines[2] }
      if ($id -match '^\d+$' -and (Get-Process -Id ([int]$id) -ErrorAction SilentlyContinue)) { Set-Content -LiteralPath $file.FullName -Value @('stopped', $env:CLAUDE_PID, $id) }
      else { Remove-Item -LiteralPath $file.FullName -Force }
    }
  }
  # This window's own waiter, still running, needs nothing (a compaction fires sessionStart again).
  # One another process started is a resume in a new Claude Code process: the old one is gone, so
  # that waiter's finish reaches nobody, and a card it confirmed would be lost. It is stopped, and
  # this window registers and gets a waiter of its own.
  if (Test-Path -LiteralPath $pidFile) {
    $lines = @(Get-Content -LiteralPath $pidFile -TotalCount 2)
    $id = [string]$lines[0]
    if ($id -match '^\d+$' -and (Get-Process -Id ([int]$id) -ErrorAction SilentlyContinue)) {
      $owner = if ($lines.Count -ge 2) { [string]$lines[1] } else { '' }
      if (-not $env:CLAUDE_PID -or -not $owner -or $owner -eq [string]$env:CLAUDE_PID) { exit 0 }
      Set-Content -LiteralPath $pidFile -Value @('stopped', $owner, $id)
    }
  }
  if ((Register $sess 3) -ne 200) { exit 0 }
  $exe = (Get-Process -Id $PID).Path
  Write-Output @"
Officium: this window is registered as an agent window (session $sess), so cards can be queued into it from the board.
Start its waiter now in the background (the shell tool's background mode), and then carry on with whatever the person asks:
    & "$exe" -NoProfile -ExecutionPolicy Bypass -File "$PSCommandPath" wait $sess
It waits as long as it takes, so it finishes only when there is something to do. When it finishes, act on its last line and on nothing else it printed:
- "OFFICIUM_CARD <KEY> <projectId>": a person queued that card into this window. Work it in that Officium project following the backlog skill, as if they had named it. When it has left its phase, start the waiter again the same way.
- "OFFICIUM_WAIT_AGAIN": its configured time limit ran out. Start the waiter again.
- "OFFICIUM_WAITER_REPLACED" or "OFFICIUM_WAITER_STOPPED <session>": another waiter took over, or a /clear ended the window it served. Do not start one, and say nothing about it.
- "OFFICIUM_WAIT_FAILED ...": tell the person why, and do not start it again.
- No such line (something stopped it): tell the person in one line that cards queued from the board will not reach this window until the waiter runs again, and do not start it again unless they ask.
"@
  exit 0
}

# The waiter.
$sess = $Session -replace '[^A-Za-z0-9_-]', ''
if (-not $sess) { Write-Output 'OFFICIUM_WAIT_FAILED no session id: run it as officium-session.ps1 wait <session_id>'; exit 1 }
if (-not $token) { Write-Output "OFFICIUM_WAIT_FAILED no heartbeat token: create one in Officium, under Connect an agent, and save it to $tokenFile"; exit 1 }
$max = [int]$env:OFFICIUM_WAIT_MAX   # 0, the default: no limit
$poll = [int]$env:OFFICIUM_WAIT_POLL
if ($poll -le 0) { $poll = 25 }

if (-not (Test-Path -LiteralPath $state)) {
  if ($env:OS -eq 'Windows_NT') { [void](New-Item -ItemType Directory -Force -Path $state) }
  else { [void][System.IO.Directory]::CreateDirectory($state, [System.IO.UnixFileMode]'UserRead, UserWrite, UserExecute') }
}
$pidFile = Join-Path $state "$sess.pid"
Set-Content -LiteralPath $pidFile -Value @([string]$PID, [string]$env:CLAUDE_PID)

function Stop-Waiter([string]$Line, [int]$Code) {
  if ([string](Get-Content -LiteralPath $pidFile -TotalCount 1) -in @([string]$PID, 'stopped')) { Remove-Item -LiteralPath $pidFile -Force }
  [Console]::Out.WriteLine($Line)   # not the pipeline: callers discard their output with [void]
  exit $Code
}
function Join-Board {
  $code = Register $sess 10
  if ($code -eq 401) { Stop-Waiter 'OFFICIUM_WAIT_FAILED the heartbeat token is unknown or was revoked' 1 }
  if ($code -eq 429) { Stop-Waiter 'OFFICIUM_WAIT_FAILED this account has too many agent windows open: close one, or take its cards out, then start the waiter again' 1 }
  return $code
}

$started = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$backoff = 1
[void](Join-Board)
$uuid = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
while ($true) {
  if ([string](Get-Content -LiteralPath $pidFile -TotalCount 1) -eq 'stopped') { Stop-Waiter "OFFICIUM_WAITER_STOPPED $sess" 0 }
  if ($max -gt 0 -and [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $started -ge $max) { Stop-Waiter 'OFFICIUM_WAIT_AGAIN' 0 }
  $answer = Invoke-Officium 'GET' "/officium/v1/sessions/$sess/next?wait=$poll" '' ($poll + 20)
  switch ($answer.Code) {
    200 {
      $backoff = 1
      $card = $null
      try { $card = $answer.Text | ConvertFrom-Json } catch { }
      $key = [string]$card.cardKey; $project = [string]$card.projectId; $cardId = [string]$card.cardId
      if ($key -cmatch '^[A-Z][A-Z0-9]{0,15}-[0-9]{1,9}$' -and $project -cmatch $uuid -and $cardId -cmatch $uuid) {
        $confirm = Invoke-Officium 'POST' "/officium/v1/sessions/$sess/confirm" (@{ cardId = $cardId } | ConvertTo-Json -Compress) 10
        if ($confirm.Code -eq 204) { Stop-Waiter "OFFICIUM_CARD $key $project" 0 }
      }
    }
    204 { $backoff = 1 }
    404 { if ((Join-Board) -ne 200) { Start-Sleep -Seconds $backoff; $backoff = [Math]::Min(30, $backoff * 2) } }
    409 { Stop-Waiter 'OFFICIUM_WAITER_REPLACED' 0 }
    401 { Stop-Waiter 'OFFICIUM_WAIT_FAILED the heartbeat token is unknown or was revoked' 1 }
    default { Start-Sleep -Seconds $backoff; $backoff = [Math]::Min(30, $backoff * 2) }
  }
}
