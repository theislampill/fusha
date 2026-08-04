#requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'launch_lane.ps1'
$canary = 'ٱلْمُلْكُ · ٱلَّذِينَ · مَا'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('fusha-launch-lane-test-' + [guid]::NewGuid())

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $promptPath = Join-Path $tempRoot 'prompt.md'
    $runDir = Join-Path $tempRoot 'run'
    [IO.File]::WriteAllText(
        $promptPath,
        "BYTE_EXACT_CANARY: $canary`nPerform the bounded task.`n",
        [Text.UTF8Encoding]::new($false)
    )

    Assert-True (Test-Path -LiteralPath $launcher) 'launch_lane.ps1 is missing (expected red-first failure)'

    $allowedTools = @(
        'Read',
        'Edit',
        'Bash(python tools/test_sample.py*)'
    )
    & $launcher -PromptPath $promptPath -Worktree $repo -RunDirectory $runDir `
        -Model 'claude-sonnet-5' -AllowedTools $allowedTools -PreflightOnly
    Assert-True ($LASTEXITCODE -eq 0) 'preflight-only invocation failed'

    $meta = Get-Content -LiteralPath (Join-Path $runDir 'metadata.json') -Raw -Encoding utf8 |
        ConvertFrom-Json
    Assert-True ($meta.status -eq 'PRECHECK_PASS') 'metadata did not record PRECHECK_PASS'
    Assert-True ($meta.requested_model -eq 'claude-sonnet-5') 'requested model drifted'
    Assert-True ($meta.fallback_model -eq $null) 'fallback model must remain disabled'
    Assert-True ($meta.claude_cli_version -eq 'not_invoked_preflight_only') `
        'preflight-only must be hermetic and must not invoke the Claude CLI'
    Assert-True ($meta.PSObject.Properties.Name -contains 'actual_session_id') `
        'metadata must predeclare actual_session_id for worker finalization'
    Assert-True ($meta.PSObject.Properties.Name -contains 'finished_at_utc') `
        'metadata must predeclare finished_at_utc for worker finalization'
    Assert-True ($meta.PSObject.Properties.Name -contains 'exit_code') `
        'metadata must predeclare exit_code for worker finalization'
    Assert-True ($meta.prompt_sha256 -match '^[0-9a-f]{64}$') 'prompt hash is missing'
    Assert-True (($meta.allowed_tools | ConvertTo-Json -Compress) -eq `
        ($allowedTools | ConvertTo-Json -Compress)) `
        'focused tool allowlist was not preserved byte-for-byte in metadata'

    $probe = Get-Content -LiteralPath (Join-Path $runDir 'preflight.stream.jsonl') `
        -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True ($probe.canary -ceq $canary) 'Arabic canary changed through the stream-file path'
    Assert-True ($probe.model -eq 'claude-sonnet-5') 'model id changed through preflight'

    $fakeClaude = Join-Path $tempRoot 'fake-claude.ps1'
    $fakeArgs = Join-Path $tempRoot 'fake-claude-args.json'
    [IO.File]::WriteAllText(
        $fakeClaude,
        @'
[IO.File]::WriteAllText(
    $env:FUSHA_LANE_TEST_ARGS,
    (($args | ConvertTo-Json -Compress) + "`n"),
    [Text.UTF8Encoding]::new($false)
)
Write-Output '{"type":"result","subtype":"success","session_id":"test-session","model":"claude-sonnet-5"}'
& git --version | Out-Null
'@,
        [Text.UTF8Encoding]::new($false)
    )
    $workerConfig = [ordered]@{
        prompt_path = $promptPath
        prompt_sha256 = $meta.prompt_sha256
        worktree = $repo
        run_directory = $runDir
        requested_model = 'claude-sonnet-5'
        permission_mode = 'acceptEdits'
        allowed_tools = $allowedTools
        session_id = 'test-session'
        claude_command = $fakeClaude
    }
    $workerConfigPath = Join-Path $runDir 'worker-config.json'
    [IO.File]::WriteAllText(
        $workerConfigPath,
        (($workerConfig | ConvertTo-Json -Depth 10) + "`n"),
        [Text.UTF8Encoding]::new($false)
    )
    $env:FUSHA_LANE_TEST_ARGS = $fakeArgs
    & pwsh -NoLogo -NoProfile -File $launcher -WorkerConfigPath $workerConfigPath
    Assert-True ($LASTEXITCODE -eq 0) 'fake worker invocation failed'
    $invokedArgs = Get-Content -LiteralPath $fakeArgs -Raw -Encoding utf8 | ConvertFrom-Json
    $allowFlag = [Array]::IndexOf([object[]]$invokedArgs, '--allowedTools')
    Assert-True ($allowFlag -ge 0) 'worker omitted --allowedTools'
    Assert-True ($invokedArgs[$allowFlag + 1] -eq ($allowedTools -join ',')) `
        'worker changed the focused tool allowlist before invoking Claude'
    $finishedMeta = Get-Content -LiteralPath (Join-Path $runDir 'metadata.json') `
        -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True ($finishedMeta.status -eq 'WORKER_COMPLETE') `
        ("fake worker did not finalize metadata as WORKER_COMPLETE: {0}" -f $finishedMeta.status)
    Remove-Item Env:FUSHA_LANE_TEST_ARGS

    $badRun = Join-Path $tempRoot 'bad-model'
    $badModelRejected = $false
    try {
        & $launcher -PromptPath $promptPath -Worktree $repo -RunDirectory $badRun `
            -Model 'sonnet' -PreflightOnly 2>$null
    }
    catch {
        $badModelRejected = $true
    }
    Assert-True $badModelRejected 'an alias or unidentified model was accepted'

    $delegationRejected = $false
    try {
        & $launcher -PromptPath $promptPath -Worktree $repo `
            -RunDirectory (Join-Path $tempRoot 'bad-delegation') `
            -Model 'claude-sonnet-5' -AllowedTools 'Task' -PreflightOnly 2>$null
    }
    catch {
        $delegationRejected = $true
    }
    Assert-True $delegationRejected 'Task was allowed through the focused tool allowlist'

    Write-Output 'launch_lane preflight PASS: PS7, strict model id, UTF-8 Arabic canary, focused allowlist and no fallback'
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
