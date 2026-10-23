$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$candidates = @('pythonw.exe', 'python.exe', 'C:\msys64\ucrt64\bin\pythonw.exe', 'C:\msys64\ucrt64\bin\python.exe')
foreach ($candidate in $candidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
        Start-Process -FilePath $command.Source -ArgumentList @('run_pet.py') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
        exit
    }
}
Write-Host 'Install Python 3.10+ with tkinter, then run python run_pet.py.'
Read-Host 'Press Enter to close'
