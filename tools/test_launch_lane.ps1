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

    & $launcher -PromptPath $promptPath -Worktree $repo -RunDirectory $runDir `
        -Model 'claude-sonnet-5' -PreflightOnly
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

    $probe = Get-Content -LiteralPath (Join-Path $runDir 'preflight.stream.jsonl') `
        -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True ($probe.canary -ceq $canary) 'Arabic canary changed through the stream-file path'
    Assert-True ($probe.model -eq 'claude-sonnet-5') 'model id changed through preflight'

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

    Write-Output 'launch_lane preflight PASS: PS7, strict model id, UTF-8 Arabic canary, metadata and no fallback'
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
