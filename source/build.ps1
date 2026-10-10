param([string]$Python = 'python', [string]$Destination = '..\app', [string]$BuildDirectory = 'build', [ValidateSet('onefile', 'onedir')][string]$Layout = 'onefile')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $Python review_build.py --destination $Destination --build-directory $BuildDirectory --layout $Layout
    if ($LASTEXITCODE -ne 0) { throw 'Tests or build failed; see the output logs. Do not distribute a partial build.' }
} finally { Pop-Location }
