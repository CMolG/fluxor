# preTool (every tool) -- the PowerShell twin of officium-temporary-refs.sh: refuses an agent's move
# of an Officium card to review while the card still has `card://<KEY> [temporary]` references in
# the code.
#
# It acts only on `cards.move` to `review` through `mcp__<mcpServer>__query` (the server name from
# <harness>/config/backlog.json, default officium). The key comes from the call's params (`cardKey`
# or `key`), else from the session's transcript, where every Officium answer that carries the card's
# id carries its key beside it. Then <harness>/skills/backlog/scripts/card_refs.py --json list <KEY>
# and, with a temporary reference left, exit 2 with each one and the fix on stderr. Nothing leaves
# the machine. It fails open: no project, no config, no card_refs.py, no python, no key, or an
# answer it cannot read, and the move goes through without a word.

$ErrorActionPreference = 'SilentlyContinue'

$payload = $null
try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { exit 0 }
$tool = [string]$payload.tool_name
if ($tool -notlike 'mcp__*__query') { exit 0 }
$toolInput = $payload.tool_input
if ([string]$toolInput.operation -ne 'cards.move') { exit 0 }
$params = $toolInput.params
if ([string]$params.status -ne 'review') { exit 0 }

$root = [string]$env:CLAUDE_PROJECT_DIR
if (-not $root) {
  $cwd = [string]$payload.cwd
  if (-not $cwd) { $cwd = (Get-Location).Path }
  $root = [string](git -C $cwd rev-parse --show-toplevel 2>$null)
}
if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) { exit 0 }
$harness = [string]$env:HARNESS_DIR
if (-not $harness) { $harness = '.harness' }
if (-not [System.IO.Path]::IsPathRooted($harness)) { $harness = Join-Path $root $harness }
$config = Join-Path $harness 'config/backlog.json'
$script = Join-Path $harness 'skills/backlog/scripts/card_refs.py'
if (-not (Test-Path -LiteralPath $config -PathType Leaf) -or -not (Test-Path -LiteralPath $script -PathType Leaf)) { exit 0 }

$server = 'officium'
try {
  $named = [string](Get-Content -LiteralPath $config -Raw | ConvertFrom-Json).mcpServer
  if ($named -match '^[A-Za-z0-9_.-]+$') { $server = $named }
} catch { }
if ($tool -ne "mcp__${server}__query") { exit 0 }

$keyPattern = '^[A-Z][A-Z0-9]*-[0-9]+$'
$key = [string]$params.cardKey
if ($key -cnotmatch $keyPattern) { $key = [string]$params.key }
if ($key -cnotmatch $keyPattern) {
  $id = [string]$params.cardId
  if ($id -cmatch $keyPattern) { $key = $id }
  else {
    if ($id -notmatch '^[0-9A-Fa-f-]{8,64}$') { exit 0 }
    $transcript = [string]$payload.transcript_path
    if (-not $transcript -or -not (Test-Path -LiteralPath $transcript -PathType Leaf)) { exit 0 }
    # The answers sit in the transcript as JSON strings inside JSON, so their quotes come escaped:
    # backslashes are dropped before matching. The last answer for this id wins.
    $s = '\s*'
    $k = '([A-Z][A-Z0-9]*-[0-9]+)'
    $pattern = "`"id`"${s}:${s}`"${id}`"${s},${s}`"projectId`"${s}:${s}`"[^`"]*`"${s},${s}`"key`"${s}:${s}`"${k}`"|`"cardId`"${s}:${s}`"${id}`"${s},${s}`"cardKey`"${s}:${s}`"${k}`""
    $key = ''
    foreach ($line in [System.IO.File]::ReadLines($transcript)) {
      if (-not $line.Contains($id)) { continue }
      foreach ($m in [regex]::Matches($line.Replace('\', ''), $pattern)) {
        $key = if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }
      }
    }
    if ($key -cnotmatch $keyPattern) { exit 0 }
  }
}

# python3 first; on Windows it is often the Store's placeholder, which fails, so then python.
$py = $null
foreach ($candidate in 'python3', 'python') {
  if (Get-Command $candidate -CommandType Application) {
    & $candidate -c pass *> $null
    if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
  }
}
if (-not $py) { exit 0 }

$env:CLAUDE_PROJECT_DIR = $root
Push-Location -LiteralPath $root
$found = (& $py $script --json list $key 2>$null) -join "`n"
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { exit 0 }
try { $refs = @(($found | ConvertFrom-Json).references) } catch { exit 0 }
$lines = @($refs | Where-Object { $_.kind -eq 'temporary' } | ForEach-Object { "$($_.file):$($_.line): $($_.text)" })
if ($lines.Count -eq 0) { exit 0 }

$message = @("officium-temporary-refs: $key still has [temporary] card references, so it does not go to review yet:") + $lines + @(
  'Resolve each one in this card, or re-point it to a follow-up card (card://<OTHER> [temporary]) that says when it goes, then move the card again (backlog skill, step 8).')
[Console]::Error.WriteLine($message -join "`n")
exit 2
