$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime'
$exe = Join-Path $runtime 'ollama\ollama.exe'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
if (-not (Test-Path -LiteralPath $exe)) {
    $release = Invoke-RestMethod 'https://api.github.com/repos/ollama/ollama/releases/latest'
    $asset = $release.assets | Where-Object name -eq 'ollama-windows-amd64.zip'
    if (-not $asset) { throw 'Official Windows portable package not found.' }
    $archive = Join-Path $runtime 'ollama.zip'
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $runtime 'ollama') -Force
}
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:OLLAMA_MODELS = Join-Path $runtime 'models'
$env:OLLAMA_NO_CLOUD = '1'
try { $null = Invoke-RestMethod 'http://127.0.0.1:11435/api/version' -TimeoutSec 2 }
catch {
    Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 4
}
& $exe pull qwen3:4b
if ($LASTEXITCODE -ne 0) { throw 'Model download failed; rerun setup to resume.' }
Write-Host 'Local model ready. Open Start-Pet.cmd.'
