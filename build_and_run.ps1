Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvRoot = "$projectRoot\.venv"
$distRoot = "$projectRoot\build\app.dist"
$distOpenVinoLibs = "$distRoot\openvino\libs"
$venvOpenVinoLibs = "$venvRoot\Lib\site-packages\openvino\libs"
$venvTokenizerLibs = "$venvRoot\Lib\site-packages\openvino_tokenizers\lib"
$modelDir = "$distRoot\models\DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
$appName = "mirrormirror-engine"
$exePath = "$distRoot\$appName.exe"

Write-Host "[1/6] Switching to project root..."
Set-Location $projectRoot

Write-Host "[2/6] Running existing build script..."
& "$projectRoot\build.ps1"

Write-Host "[3/6] Stopping previous backend processes (if any)..."
Get-Process $appName -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "[4/6] Restoring OpenVINO runtime DLL layout..."
robocopy $venvOpenVinoLibs $distOpenVinoLibs *.dll | Out-Null

$venvPluginsXml = "$venvOpenVinoLibs\plugins.xml"
$distPluginsXml = "$distOpenVinoLibs\plugins.xml"
if (Test-Path $venvPluginsXml) {
        Copy-Item $venvPluginsXml $distPluginsXml -Force
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
}

Write-Host "[5/6] Restoring tokenizer runtime DLLs to dist root..."
Copy-Item "$venvTokenizerLibs\openvino_tokenizers.dll" "$distRoot\" -Force
Copy-Item "$venvTokenizerLibs\icudt70.dll" "$distRoot\" -Force
Copy-Item "$venvTokenizerLibs\icuuc70.dll" "$distRoot\" -Force

Write-Host "[6/6] Removing accidental copy-suffixed DLL duplicates..."
Remove-Item "$distRoot\* copy.dll" -ErrorAction SilentlyContinue

Write-Host "Validating critical files..."
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

# Write-Host "Setting runtime environment variables..."
# $env:PATH = "$distOpenVinoLibs;$distRoot;$env:PATH"
# $env:OPENVINO_LIB_PATH = $distOpenVinoLibs
# $env:OPENVINO_MODEL_DIR = $modelDir

# Write-Host "Launching packaged backend..."
# & $exePath
