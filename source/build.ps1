param([string]$Python = 'python', [string]$Destination = '..\app', [string]$BuildDirectory = 'build')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; executable was not built.' }
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name KKSInstaller --distpath $Destination --workpath (Join-Path $BuildDirectory 'pyinstaller') --specpath $BuildDirectory launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
} finally { Pop-Location }
