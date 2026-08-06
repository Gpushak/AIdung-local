$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$OutputDir = Join-Path $ProjectRoot "App_finale"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"

Write-Host "Building AI Dungeon Master..."

if (Test-Path $OutputDir) {
    Remove-Item -Recurse -Force $OutputDir
}
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name "AI_Dungeon_Master" `
    --collect-data customtkinter `
    --hidden-import tiktoken_ext.openai_public `
    --hidden-import tiktoken_ext `
    --distpath $DistDir `
    --workpath $BuildDir `
    (Join-Path $ProjectRoot "run_dungeon.py")

New-Item -ItemType Directory -Path $OutputDir | Out-Null
Copy-Item (Join-Path $DistDir "AI_Dungeon_Master.exe") $OutputDir

$WorldsDest = Join-Path $OutputDir "worlds"
New-Item -ItemType Directory -Path $WorldsDest | Out-Null

$SettingsSrc = Join-Path $ProjectRoot "worlds\settings.json"
if (Test-Path $SettingsSrc) {
    Copy-Item $SettingsSrc $WorldsDest
} else {
    @'
{
  "api_url": "http://localhost:1234/v1/chat/completions",
  "api_key": "",
  "temperature": 0.7,
  "max_tokens": 300,
  "context_size": 16384,
  "summary_interval": 10,
  "memory_interval": 5,
  "memory_top_k": 5,
  "stream_mode": true,
  "summary_enabled": true,
  "memory_enabled": true
}
'@ | Set-Content -Path (Join-Path $WorldsDest "settings.json") -Encoding UTF8
}

Write-Host "Done: $OutputDir\AI_Dungeon_Master.exe"
