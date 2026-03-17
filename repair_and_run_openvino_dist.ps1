Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvRoot = "$projectRoot\.venv"
$distRoot = "$projectRoot\build\app.dist"
$distOpenVinoLibs = "$distRoot\openvino\libs"
$venvOpenVinoLibs = "$venvRoot\Lib\site-packages\openvino\libs"
$venvTokenizerLibs = "$venvRoot\Lib\site-packages\openvino_tokenizers\lib"
$modelDir = "$distRoot\models\qwen3-1.7b-int4-ov"
$appName = "mirrormirror-engine"
$exePath = "$distRoot\$appName.exe"

Write-Host "[1/5] Switching to project root..."
Set-Location $projectRoot

Write-Host "[2/5] Stopping previous backend processes (if any)..."
Get-Process $appName -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "[3/5] Restoring OpenVINO runtime DLLs into dist..."
robocopy $venvOpenVinoLibs $distOpenVinoLibs *.dll | Out-Null
robocopy $venvOpenVinoLibs $distRoot *.dll | Out-Null

$venvPluginsXml = "$venvOpenVinoLibs\plugins.xml"
$distPluginsXml = "$distOpenVinoLibs\plugins.xml"
if (Test-Path $venvPluginsXml) {
    Copy-Item $venvPluginsXml $distPluginsXml -Force
    Copy-Item $venvPluginsXml "$distRoot\plugins.xml" -Force
}
elseif (-not (Test-Path $distPluginsXml)) {
    $pluginsXmlContent = @"
<ie>
  <plugins>
    <plugin name="CPU" location="openvino_intel_cpu_plugin.dll"/>
  </plugins>
</ie>
"@
    Set-Content -Path $distPluginsXml -Value $pluginsXmlContent -Encoding UTF8
    Set-Content -Path "$distRoot\plugins.xml" -Value $pluginsXmlContent -Encoding UTF8
}

Write-Host "[4/5] Restoring tokenizer runtime DLLs and cleaning duplicates..."
Copy-Item "$venvTokenizerLibs\openvino_tokenizers.dll" "$distRoot\" -Force
Copy-Item "$venvTokenizerLibs\icudt70.dll" "$distRoot\" -Force
Copy-Item "$venvTokenizerLibs\icuuc70.dll" "$distRoot\" -Force
Remove-Item "$distRoot\* copy.dll" -ErrorAction SilentlyContinue

$criticalPaths = @(
    "$distOpenVinoLibs\openvino_intel_cpu_plugin.dll",
    "$distOpenVinoLibs\openvino.dll",
    "$distOpenVinoLibs\plugins.xml",
    "$distRoot\openvino_tokenizers.dll",
    "$distRoot\icudt70.dll",
    "$distRoot\icuuc70.dll",
    $modelDir,
    $exePath
)

$missing = @()
foreach ($path in $criticalPaths) {
    if (-not (Test-Path $path)) {
        $missing += $path
    }
}

if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing required files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "[5/5] Setting runtime environment and launching app..."
$env:PATH = "$distRoot;$distOpenVinoLibs;$env:PATH"
$env:OPENVINO_LIB_PATH = $distOpenVinoLibs
$env:OPENVINO_MODEL_DIR = $modelDir
$env:FLASK_SECRET_KEY = "changmeplease"
$env:JWT_SECRET_KEY = "changmeplease"

& $exePath
