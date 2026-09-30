$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if ([Environment]::Is64BitOperatingSystem -eq $false -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Build on Windows x64 with x64 Python 3.12' }
# py.exe needs its version argument split from the executable.
if ($env:PYTHON) { & $env:PYTHON -m venv build\editor-venv-win } else { py -3.12 -m venv build\editor-venv-win }
if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment' }
$venv = 'build\editor-venv-win\Scripts\python.exe'
& $venv -m pip install -r editor\requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
& $venv -m unittest discover -s tests -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $venv -m PyInstaller --noconfirm --clean --windowed --onedir --name KeybowEditor --collect-all webview `
  --icon "$(Resolve-Path editor\assets\keybow-icon.ico)" `
  --distpath build\editor-dist-win --workpath build\editor-work-win --specpath build `
  --paths editor --add-data "$(Resolve-Path editor\static):static" editor\launch.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Copy-Item THIRD_PARTY_NOTICES.md build\editor-dist-win\KeybowEditor\THIRD_PARTY_NOTICES.md -Force
Copy-Item editor\LICENSE build\editor-dist-win\KeybowEditor\KeybowEditorLicense.txt -Force
$pythonLicense = & $venv packaging\python-license-path.py
if ($LASTEXITCODE -ne 0) { throw 'Python license not found' }
Copy-Item $pythonLicense build\editor-dist-win\KeybowEditor\PythonLicense.txt -Force
Compress-Archive -Path 'build\editor-dist-win\KeybowEditor' -DestinationPath 'build\keybow-editor-windows-x64.zip' -Force
Write-Output 'build\keybow-editor-windows-x64.zip'
