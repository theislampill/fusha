#requires -Version 7.0
[CmdletBinding(DefaultParameterSetName = 'Launch')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Launch')]
    [string]$PromptPath,

    [Parameter(Mandatory, ParameterSetName = 'Launch')]
    [string]$Worktree,

    [Parameter(Mandatory, ParameterSetName = 'Launch')]
    [string]$RunDirectory,

    [Parameter(Mandatory, ParameterSetName = 'Launch')]
    [ValidateSet('claude-sonnet-5', 'claude-opus-5')]
    [string]$Model,

    [Parameter(ParameterSetName = 'Launch')]
    [ValidateSet('manual', 'acceptEdits', 'auto')]
    [string]$PermissionMode = 'manual',

    [Parameter(ParameterSetName = 'Launch')]
    [string[]]$AllowedTools = @(),

    [Parameter(ParameterSetName = 'Launch')]
    [switch]$PreflightOnly,

    [Parameter(Mandatory, ParameterSetName = 'Worker')]
    [string]$WorkerConfigPath
)

$ErrorActionPreference = 'Stop'
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$canary = 'ٱلْمُلْكُ · ٱلَّذِينَ · مَا'

function Write-JsonFile([string]$Path, [object]$Value) {
    $json = $Value | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($Path, $json + "`n", [Text.UTF8Encoding]::new($false))
}

function Get-Sha256([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Get-GitValue([string]$Directory, [string[]]$Arguments) {
    $value = & git -C $Directory @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git command failed in $Directory" }
    return ($value -join "`n").Trim()
}

function Invoke-LaneWorker([string]$ConfigPath) {
    $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
    $metadataPath = Join-Path $config.run_directory 'metadata.json'
    try {
        if ((Get-Sha256 $config.prompt_path) -ne $config.prompt_sha256) {
            throw 'prompt changed after preflight'
        }
        Set-Location -LiteralPath $config.worktree
        $streamPath = Join-Path $config.run_directory 'stream.jsonl'
        $stderrPath = Join-Path $config.run_directory 'stderr.log'
        $prompt = [IO.File]::ReadAllText($config.prompt_path, $utf8)

        $claudeArgs = @(
            '-p',
            '--model', $config.requested_model,
            '--output-format', 'stream-json',
            '--verbose',
            '--session-id', $config.session_id,
            '--permission-mode', $config.permission_mode,
            '--disallowedTools', 'Task,EnterWorktree'
        )
        if (@($config.allowed_tools).Count -gt 0) {
            $claudeArgs += @('--allowedTools', (@($config.allowed_tools) -join ','))
        }
        $prompt | & $config.claude_command @claudeArgs 1> $streamPath 2> $stderrPath
        $code = $LASTEXITCODE
        [IO.File]::WriteAllText(
            (Join-Path $config.run_directory 'exit-code.txt'),
            "$code`n",
            [Text.UTF8Encoding]::new($false)
        )

        $result = $null
        if (Test-Path -LiteralPath $streamPath) {
            foreach ($line in [IO.File]::ReadLines($streamPath, $utf8)) {
                if (-not [string]::IsNullOrWhiteSpace($line)) {
                    try {
                        $record = $line | ConvertFrom-Json
                        if ($record.type -eq 'result') { $result = $record }
                    }
                    catch { }
                }
            }
        }
        if ($null -ne $result) {
            Write-JsonFile (Join-Path $config.run_directory 'result.json') $result
        }

        $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding utf8 | ConvertFrom-Json
        $actualModels = @()
        if ($null -ne $result) {
            if ($result.PSObject.Properties.Name -contains 'model' -and $result.model) {
                $actualModels += [string]$result.model
            }
            if ($result.PSObject.Properties.Name -contains 'modelUsage' -and $result.modelUsage) {
                $actualModels += @($result.modelUsage.PSObject.Properties.Name)
            }
            if ($result.PSObject.Properties.Name -contains 'session_id' -and $result.session_id) {
                $metadata.actual_session_id = [string]$result.session_id
            }
        }
        $metadata.actual_models = @($actualModels | Sort-Object -Unique)
        $metadata.exit_code = $code
        $metadata.finished_at_utc = [DateTime]::UtcNow.ToString('o')
        $metadata.status = if ($code -eq 0 -and $null -ne $result) {
            'WORKER_COMPLETE'
        }
        elseif ($code -ne 0) {
            'WORKER_EXIT_NONZERO'
        }
        else {
            'ORCHESTRATOR_TRANSPORT_FAILURE'
        }
        Write-JsonFile $metadataPath $metadata
        exit $code
    }
    catch {
        $failure = [ordered]@{
            schema = 'fusha.lane_launch_failure.v1'
            status = 'ORCHESTRATOR_TRANSPORT_FAILURE'
            message = $_.Exception.Message
            finished_at_utc = [DateTime]::UtcNow.ToString('o')
        }
        Write-JsonFile (Join-Path $config.run_directory 'transport-failure.json') $failure
        [IO.File]::WriteAllText(
            (Join-Path $config.run_directory 'exit-code.txt'),
            "125`n",
            [Text.UTF8Encoding]::new($false)
        )
        exit 125
    }
}

if ($PSCmdlet.ParameterSetName -eq 'Worker') {
    Invoke-LaneWorker ([IO.Path]::GetFullPath($WorkerConfigPath))
}

if ($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -ne 7) {
    throw 'tools/launch_lane.ps1 requires PowerShell 7.x'
}
if ($AllowedTools | Where-Object { $_ -in @('Task', 'EnterWorktree') }) {
    throw 'Task and EnterWorktree remain prohibited even when a focused allowlist is supplied'
}

$promptFull = [IO.Path]::GetFullPath($PromptPath)
$worktreeFull = [IO.Path]::GetFullPath($Worktree)
$runFull = [IO.Path]::GetFullPath($RunDirectory)
if (-not (Test-Path -LiteralPath $promptFull -PathType Leaf)) { throw 'prompt file does not exist' }
if (-not (Test-Path -LiteralPath $worktreeFull -PathType Container)) { throw 'worktree does not exist' }
[void][IO.File]::ReadAllText($promptFull, $utf8)
New-Item -ItemType Directory -Path $runFull -Force | Out-Null

$preflightRecord = [ordered]@{
    schema = 'fusha.lane_preflight.v1'
    canary = $canary
    model = $Model
}
[IO.File]::WriteAllText(
    (Join-Path $runFull 'preflight.stream.jsonl'),
    (($preflightRecord | ConvertTo-Json -Compress) + "`n"),
    [Text.UTF8Encoding]::new($false)
)
$roundTrip = Get-Content -LiteralPath (Join-Path $runFull 'preflight.stream.jsonl') `
    -Raw -Encoding utf8 | ConvertFrom-Json
if ($roundTrip.canary -cne $canary -or $roundTrip.model -ne $Model) {
    throw 'preflight stream round-trip changed the Arabic canary or model id'
}

$sessionId = [guid]::NewGuid().ToString()
$claudeCommand = $null
$cliVersion = 'not_invoked_preflight_only'
if (-not $PreflightOnly) {
    $claudeCommand = (Get-Command claude -ErrorAction Stop).Source
    $cliVersion = (& claude --version 2>$null | Select-Object -First 1).Trim()
}
$metadata = [ordered]@{
    schema = 'fusha.lane_launch_metadata.v1'
    status = 'PRECHECK_PASS'
    requested_model = $Model
    actual_models = @()
    actual_session_id = $null
    fallback_model = $null
    claude_cli_version = $cliVersion
    session_id = $sessionId
    start_sha = Get-GitValue $worktreeFull @('rev-parse', 'HEAD')
    branch = Get-GitValue $worktreeFull @('branch', '--show-current')
    worktree = $worktreeFull
    prompt_path = $promptFull
    prompt_sha256 = Get-Sha256 $promptFull
    permission_mode = $PermissionMode
    allowed_tools = @($AllowedTools)
    disallowed_tools = @('Task', 'EnterWorktree')
    started_at_utc = [DateTime]::UtcNow.ToString('o')
    finished_at_utc = $null
    exit_code = $null
}
$metadataPath = Join-Path $runFull 'metadata.json'
Write-JsonFile $metadataPath $metadata
if ($PreflightOnly) { exit 0 }

$config = [ordered]@{
    prompt_path = $promptFull
    prompt_sha256 = $metadata.prompt_sha256
    worktree = $worktreeFull
    run_directory = $runFull
    requested_model = $Model
    permission_mode = $PermissionMode
    allowed_tools = @($AllowedTools)
    session_id = $sessionId
    claude_command = $claudeCommand
}
$configPath = Join-Path $runFull 'worker-config.json'
Write-JsonFile $configPath $config

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$quotedScript = '"' + $PSCommandPath + '"'
$quotedConfig = '"' + $configPath + '"'
$process = Start-Process -FilePath $pwsh -WindowStyle Hidden -PassThru -ArgumentList @(
    '-NoLogo', '-NoProfile', '-File', $quotedScript, '-WorkerConfigPath', $quotedConfig
)
$metadata.status = 'LAUNCHED'
$metadata.launcher_process_id = $process.Id
Write-JsonFile $metadataPath $metadata
[IO.File]::WriteAllText(
    (Join-Path $runFull 'launcher.pid'),
    "$($process.Id)`n",
    [Text.UTF8Encoding]::new($false)
)
Write-Output ("LAUNCHED session={0} pid={1} run={2}" -f $sessionId, $process.Id, $runFull)
