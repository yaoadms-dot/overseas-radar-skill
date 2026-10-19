[CmdletBinding()]
param([string]$ProjectPath, [string]$Stage='基准完整性', [ValidateSet('project','mother')][string]$Mode='project', [switch]$Probe)
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
try {
    $python = (Get-Command python -ErrorAction Stop).Source
    $engine = Join-Path $PSScriptRoot 'baseline.py'
    if ($Probe) { & $python $engine probe; exit $LASTEXITCODE }
    $arguments = @($engine, 'check', '--mode', $Mode, '--stage', $Stage)
    if ($Mode -eq 'project') {
        if ([string]::IsNullOrWhiteSpace($ProjectPath)) { throw 'ProjectPath is required.' }
        $arguments += @('--project', $ProjectPath)
    }
    & $python @arguments
    exit $LASTEXITCODE
} catch {
    @{schema_version=1;ok=$false;exit_code=2;error=@{code='ENTRYPOINT_ERROR';message=$_.Exception.Message}} | ConvertTo-Json -Depth 5
    exit 2
}
