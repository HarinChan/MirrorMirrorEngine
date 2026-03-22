Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvRoot = Join-Path $projectRoot ".venv"
$entryPoint = Join-Path $projectRoot "app.py"
$appName = "mirrormirror-engine"

$distRoot = Join-Path $projectRoot "build\app.dist"
$distOpenVinoLibs = Join-Path $distRoot "openvino\libs"
$venvOpenVinoLibs = Join-Path $venvRoot "Lib\site-packages\openvino\libs"
$venvTokenizerLibs = Join-Path $venvRoot "Lib\site-packages\openvino_tokenizers\lib"

$modelSource = Join-Path $projectRoot "models\DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
$modelDist = Join-Path $distRoot "models\DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
$envFile = Join-Path $projectRoot ".env"
$penpalsDbDir = Join-Path $projectRoot "penpals_db"
$chromaDbDir = Join-Path $projectRoot "chroma_db"
$assetDir = Join-Path $projectRoot "asset"

Set-Location $projectRoot
& (Join-Path $venvRoot "Scripts\Activate.ps1")

$nuitkaArgs = @(
  "-m", "nuitka",
  "--standalone",
  "--follow-imports",
  "--assume-yes-for-downloads",
  "--output-dir=build",
  "--output-filename=$appName",
  "--include-package=openvino",
  "--include-package-data=openvino",
  "--include-package=openvino_tokenizers",
  "--include-package-data=openvino_tokenizers",
  "--include-package=openvino_genai",
  "--include-package-data=openvino_genai",
  "--include-package=chromadb",
  "--include-package-data=chromadb",
  "--include-package=faster_whisper",
  "--include-package-data=faster_whisper",
  "--include-data-dir=$venvOpenVinoLibs=openvino\libs"
)

if (Test-Path $envFile) {
  $nuitkaArgs += "--include-data-file=$envFile=.env"
  $nuitkaArgs += "--include-data-file=$envFile=src\.env"
}

if (Test-Path $penpalsDbDir) {
  $nuitkaArgs += "--include-data-dir=$penpalsDbDir=penpals_db"
}

if (Test-Path $chromaDbDir) {
  $nuitkaArgs += "--include-data-dir=$chromaDbDir=chroma_db"
}

if (Test-Path $assetDir) {
  $nuitkaArgs += "--include-data-dir=$assetDir=asset"
}

if (Test-Path $modelSource) {
  $nuitkaArgs += "--include-data-dir=$modelSource=models\DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
}

$nuitkaArgs += $entryPoint
python @nuitkaArgs

# Manual DLL repair pass remains necessary for OpenVINO/tokenizer reliability.
robocopy $venvOpenVinoLibs $distOpenVinoLibs *.dll | Out-Null
robocopy $venvOpenVinoLibs $distRoot *.dll | Out-Null
robocopy $venvTokenizerLibs $distRoot *.dll | Out-Null

$venvPluginsXml = Join-Path $venvOpenVinoLibs "plugins.xml"
$distPluginsXml = Join-Path $distOpenVinoLibs "plugins.xml"
if (Test-Path $venvPluginsXml) {
  Copy-Item $venvPluginsXml $distPluginsXml -Force
  Copy-Item $venvPluginsXml (Join-Path $distRoot "plugins.xml") -Force
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
  Set-Content -Path (Join-Path $distRoot "plugins.xml") -Value $pluginsXmlContent -Encoding UTF8
}

if (Test-Path $modelSource) {
  robocopy $modelSource $modelDist /E | Out-Null
}

 