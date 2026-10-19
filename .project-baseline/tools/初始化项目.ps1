[CmdletBinding()]
param([string]$Name, [string]$TargetPath, [switch]$Probe)
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
try {
    $python = (Get-Command python -ErrorAction Stop).Source
    $engine = Join-Path $PSScriptRoot 'baseline.py'
    if ($Probe) { & $python $engine probe; exit $LASTEXITCODE }
    if ([string]::IsNullOrWhiteSpace($Name) -or [string]::IsNullOrWhiteSpace($TargetPath)) { throw 'Name and TargetPath are required.' }
    & $python $engine init --name $Name --target $TargetPath
    exit $LASTEXITCODE
} catch {
    @{schema_version=1;ok=$false;exit_code=2;error=@{code='ENTRYPOINT_ERROR';message=$_.Exception.Message}} | ConvertTo-Json -Depth 5
    exit 2
}
