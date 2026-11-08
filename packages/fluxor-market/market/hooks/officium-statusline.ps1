# statusLine -- the window's bar, and its telemetry for Officium's board. The PowerShell twin of
# officium-statusline.sh, which explains the design; in short:
#
# It prints one short line (model · effort · context · cost · 5 h limit) and reports the window's
# state to Officium from a detached process: at most once per OFFICIUM_TELEMETRY_INTERVAL seconds
# (default 10), at once on a change of model, effort, fast mode or thinking, and one held-back report
# sends the newest update when the interval ends. It draws the bar and reports nothing with no token,
# no session, or in an autonomous loop (AUTOLOOP_SLOT set, or OFFICIUM_SESSIONS=0). Token and API as
# officium-statusline.sh; the token stays inside the process.
#
#   officium-statusline.ps1                          the status line (stdin: Claude Code's JSON)
#   officium-statusline.ps1 post <session> <ms>      the detached report, after waiting <ms>

param([string]$Mode = '', [string]$Session = '', [string]$DelayMs = '0')
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8   # the bar's middle dots, on a console that defaults to OEM
$Invariant = [Globalization.CultureInfo]::InvariantCulture

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
$root = $env:XDG_RUNTIME_DIR
if (-not $root) { $root = Join-Path (Get-HomeDir) '.cache' }
$state = Join-Path $root 'officium/statusline'
function Now-Ms { [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() }

function Num($v) { if ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal]) { return $v } return $null }
function Int($v) { $n = Num $v; if ($null -eq $n) { return $null } return [long][Math]::Round([double]$n, [MidpointRounding]::AwayFromZero) }
function Str($v) { if ($v -is [string] -and $v -ne '') { return $v } return $null }
function Bool($v) { if ($v -is [bool]) { return $v } return $null }
function Instant($v) {
  $n = Int $v
  if ($null -eq $n) { return $null }
  return [DateTimeOffset]::FromUnixTimeSeconds($n).UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'.000Z'", $Invariant)
}

# The flat body Officium's telemetry route takes, with only what Claude Code sent.
function Get-Telemetry($in) {
  $ctx = $in.context_window; $cost = $in.cost; $limits = $in.rate_limits; $ws = $in.workspace; $repo = $ws.repo
  $repoName = $null
  if ((Str $repo.host) -and (Str $repo.owner) -and (Str $repo.name)) { $repoName = "$($repo.host)/$($repo.owner)/$($repo.name)" }
  $all = [ordered]@{
    contextUsedPercent = Num $ctx.used_percentage; contextInputTokens = Int $ctx.total_input_tokens
    contextWindowSize = Int $ctx.context_window_size; modelId = Str $in.model.id; modelName = Str $in.model.display_name
    effort = Str $in.effort.level; thinking = Bool $in.thinking.enabled; fastMode = Bool $in.fast_mode
    costUsd = Num $cost.total_cost_usd; durationMs = Int $cost.total_duration_ms; apiDurationMs = Int $cost.total_api_duration_ms
    linesAdded = Int $cost.total_lines_added; linesRemoved = Int $cost.total_lines_removed
    fiveHourUsedPercent = Num $limits.five_hour.used_percentage; fiveHourResetsAt = Instant $limits.five_hour.resets_at
    sevenDayUsedPercent = Num $limits.seven_day.used_percentage; sevenDayResetsAt = Instant $limits.seven_day.resets_at
    sessionName = Str $in.session_name; projectDir = Str $ws.project_dir; gitWorktree = Str $ws.git_worktree
    repo = $repoName; prNumber = Int $in.pr.number; prUrl = Str $in.pr.url; version = Str $in.version
  }
  $body = [ordered]@{}
  foreach ($k in $all.Keys) { if ($null -ne $all[$k]) { $body[$k] = $all[$k] } }
  return $body
}

function Get-Bar($t) {
  $name = $t['modelName']
  if (-not $name) { $name = $t['modelId'] }
  if (-not $name) { $name = 'Claude' }
  $parts = @($name)
  if ($t['effort']) { $parts += $t['effort'] }
  if ($t.Contains('contextUsedPercent')) { $parts += ('ctx {0}%' -f (Int $t['contextUsedPercent'])) }
  if ($t.Contains('costUsd')) { $parts += ('$' + ([double]$t['costUsd']).ToString('F2', $Invariant)) }
  if ($t.Contains('fiveHourUsedPercent')) { $parts += ('5h {0}%' -f (Int $t['fiveHourUsedPercent'])) }
  # The dot as a code point: Windows PowerShell 5.1 reads a script without a BOM as ANSI.
  return ($parts -join " $([char]0x00B7) ")
}

function Send-Telemetry([string]$Sess, [int]$Delay) {
  if ($Delay -gt 0) { Start-Sleep -Milliseconds $Delay }
  $latest = Join-Path $state "$Sess.latest"
  $json = [string](Get-Content -LiteralPath $latest -Raw)
  if ($Delay -gt 0) {
    Remove-Item -LiteralPath (Join-Path $state "$Sess.pending") -Force
    if ($json) {
      $sig = ([string](Get-Content -LiteralPath (Join-Path $state "$Sess.sig") -TotalCount 1)) -replace '^\S+ ', ''
      Set-Content -LiteralPath (Join-Path $state "$Sess.sig") -Value "$(Now-Ms) $sig"
    }
  }
  if (-not $json) { return }
  $api = [string]$env:OFFICIUM_API_URL
  if (-not $api) { $api = '{{OFFICIUM_API}}' }
  if ($api.StartsWith('{{')) { $api = 'https://javadaba.com/api' }
  Invoke-WebRequest -UseBasicParsing -Method Put -Uri "$($api.TrimEnd('/'))/officium/v1/sessions/$Sess/telemetry" -TimeoutSec 3 `
    -Headers @{ Authorization = "Bearer $(Read-Token)" } -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes($json.Trim())) | Out-Null
}

if ($Mode -eq 'post') {
  if ($Session -match '^[A-Za-z0-9_-]{1,128}$' -and $DelayMs -match '^\d+$') { Send-Telemetry $Session ([int]$DelayMs) }
  exit 0
}

$in = $null
try { $in = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { }
$telemetry = Get-Telemetry $in
[Console]::Out.WriteLine((Get-Bar $telemetry))

if ($env:AUTOLOOP_SLOT -or $env:OFFICIUM_SESSIONS -eq '0') { exit 0 }
$sess = [string]$in.session_id
if ($sess -notmatch '^[A-Za-z0-9_-]{1,128}$' -or -not (Read-Token)) { exit 0 }
if (-not (Test-Path -LiteralPath $state)) {
  if ($env:OS -eq 'Windows_NT') { [void](New-Item -ItemType Directory -Force -Path $state) }
  else { [void][System.IO.Directory]::CreateDirectory($state, [System.IO.UnixFileMode]'UserRead, UserWrite, UserExecute') }
}

# Whether this update reports now, later, or rides a report already waiting.
$seconds = [int]$env:OFFICIUM_TELEMETRY_INTERVAL
if ($seconds -le 0) { $seconds = 10 }
$interval = $seconds * 1000
$now = Now-Ms
Set-Content -LiteralPath (Join-Path $state "$sess.latest") -Value ($telemetry | ConvertTo-Json -Compress)
$sig = '{0}|{1}|{2}|{3}' -f $telemetry['modelId'], $telemetry['effort'], $telemetry['fastMode'], $telemetry['thinking']
$last = [string](Get-Content -LiteralPath (Join-Path $state "$sess.sig") -TotalCount 1)
$lastAt = 0; $lastSig = $null
if ($last -match '^(\d+) (.*)$') { $lastAt = [long]$Matches[1]; $lastSig = $Matches[2] }
if (-not $last -or $now - $lastAt -ge $interval -or $lastSig -ne $sig) {
  Set-Content -LiteralPath (Join-Path $state "$sess.sig") -Value "$now $sig"
  $delay = 0
} else {
  $pending = Join-Path $state "$sess.pending"
  $mark = [string](Get-Content -LiteralPath $pending -TotalCount 1)
  if ($mark -match '^\d+$' -and $now - [long]$mark -lt 2 * $interval) { exit 0 }   # one already waits
  Set-Content -LiteralPath $pending -Value $now
  $delay = [Math]::Max(0, $lastAt + $interval - $now)
}
$arguments = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", 'post', $sess, [string]$delay)
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
