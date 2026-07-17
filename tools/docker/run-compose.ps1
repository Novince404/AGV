[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArguments
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VersionFile = Join-Path $ProjectRoot "VERSION"
$EnvironmentFile = Join-Path $ProjectRoot "deploy\compose.env"

if (-not (Test-Path -LiteralPath $VersionFile)) {
    throw "VERSION was not found at $VersionFile."
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Create deploy\compose.env from deploy\compose.env.example before using Docker Compose."
}

$env:AGV_VERSION = (Get-Content -LiteralPath $VersionFile -Raw).Trim()
if (-not $env:AGV_VERSION) {
    throw "VERSION must contain a release identifier."
}

Push-Location $ProjectRoot
try {
    & docker compose --env-file deploy/compose.env @ComposeArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
