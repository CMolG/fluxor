# sessionStart -- prints the backlog skill's session order ("A session, in order") with this project's
# id and this machine's name. Sends nothing. The PowerShell twin of backlog-session-start.sh, which
# says where the harness, the config and the machine name come from.

$ErrorActionPreference = 'SilentlyContinue'
$harness = $env:HARNESS_DIR
if (-not $harness) {
    $root = $env:CLAUDE_PROJECT_DIR
    if (-not $root) { $root = git rev-parse --show-toplevel 2>$null }
    if (-not $root) { $root = (Get-Location).Path }
    $harness = Join-Path $root '.harness'
}
$config = Join-Path $harness 'config/backlog.json'
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { exit 0 }
$json = $null
try { $json = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json } catch { }
if (-not $json) { exit 0 }

# Only names made of these characters reach the agent's context: the file is data, not instructions.
$safe = '^[A-Za-z0-9._-]{1,128}$'
$project = [string]$json.project.id
if ($project -notmatch $safe) { $project = '' }
$provider = [string]$json.provider
if ($provider -notmatch $safe) { $provider = 'officium' }

$machine = $env:AUTOLOOP_MACHINE
if (-not $machine) {
    $setting = [string]$json.machineName
    if ($setting -like 'env:*') {
        $var = $setting.Substring(4)
        if ($var -match '^[A-Za-z_][A-Za-z0-9_]*$') { $machine = [Environment]::GetEnvironmentVariable($var) }
    } elseif ($setting -and $setting -ne 'hostname') {
        $machine = $setting
    }
    if (-not $machine) { $machine = $env:COMPUTERNAME }
    if (-not $machine) { $machine = [string](hostname) }
}
if ($machine -notmatch $safe) { $machine = '' }

if ($provider -eq 'officium') {
    $id = if ($project) { $project } else { '<discover it: cards are under a project>' }
    $m = if ($machine) { $machine } else { '<this machine>' }
    @(
        "Backlog: before picking any work, follow the backlog skill's `"A session, in order`" (Officium project $id, machine $m):"
        "1. cards.working {projectId: `"$id`"}: who is on what right now."
        "2. cards.resumable {projectId: `"$id`", machine: `"$m`"}: a card this machine left unfinished is finished first."
        "3. cards.search {projectId: `"$id`", humanEditPending: true}: read each card a person changed, act, then cards.acknowledgeHumanEdit."
        "4. cards.needsHuman {projectId: `"$id`"}: what waits on a person; never yours to do."
        "5. cards.next {projectId: `"$id`"}: then the next card."
        "Pass machine `"$m`" on every call that takes one."
    ) | ForEach-Object { [Console]::Out.WriteLine($_) }
} else {
    $where = ''
    if ($project) { $where += " (project $project)" }
    if ($machine) { $where += ", machine $machine" }
    [Console]::Out.WriteLine("Backlog: before picking any work, follow the backlog skill's `"A session, in order`" through its $provider adapter${where}:")
    [Console]::Out.WriteLine('listWorking, listResumable(machine) and finish what this machine left, listHumanEdited (acknowledge each), listNeedsHuman, then nextCard.')
}
exit 0
