param([string]$Python = 'python', [string]$Destination = '..\app', [string]$BuildDirectory = 'build')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $Python review_build.py --destination $Destination --build-directory $BuildDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Tests or build failed; see the output logs. Do not distribute a partial build.' }
} finally { Pop-Location }
