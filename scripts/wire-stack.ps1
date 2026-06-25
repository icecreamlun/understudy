param(
  [switch]$StartModel,
  [switch]$RunOpenClawCheck,
  [switch]$RunNemoClawOnboard
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "env.ps1")

$Root = $env:HACKATHON_ROOT
$RuntimeDir = Join-Path $Root ".runtime"
$WorkspaceDir = Join-Path $Root "workspace"
$LogDir = Join-Path $RuntimeDir "logs"
$GeneratedModelfile = Join-Path $RuntimeDir "Modelfile.qwen3-30b-a3b"

New-Item -ItemType Directory -Force -Path `
  $RuntimeDir,
  $WorkspaceDir,
  $LogDir,
  $env:OPENCLAW_HOME,
  $env:OPENCLAW_STATE_DIR,
  (Join-Path $env:OPENCLAW_STATE_DIR "agents\main\agent") | Out-Null

function Test-CommandExists {
  param([Parameter(Mandatory)][string]$Name)
  return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-HttpOk {
  param([Parameter(Mandatory)][string]$Url)
  try {
    Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Wait-Ollama {
  for ($i = 0; $i -lt 20; $i++) {
    if (Test-HttpOk "http://127.0.0.1:11434/api/tags") {
      return $true
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Write-GeneratedModelfile {
  $lines = @(
    "FROM $($env:QWEN_MODEL_PATH)",
    "",
    "PARAMETER num_ctx 32768",
    "PARAMETER temperature 0.2",
    "PARAMETER top_p 0.95",
    "",
    "SYSTEM """"""",
    "You are a local offline business AI agent running on the Dell/NVIDIA hackathon stack.",
    "Use only local context, local tools, and documents provided in the workspace.",
    "When evidence is missing, say what is missing. Prefer concise, cited risk analysis.",
    """"""""
  )
  Set-Content -LiteralPath $GeneratedModelfile -Value $lines -Encoding ascii
}

function Get-OllamaModelNames {
  try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 10
    return @($tags.models | ForEach-Object { $_.name })
  } catch {
    return @()
  }
}

function Ensure-OllamaModel {
  if (-not (Test-CommandExists "ollama")) {
    throw "ollama is not on PATH. Install/start Ollama first, then rerun with -StartModel."
  }

  if (-not (Test-HttpOk "http://127.0.0.1:11434/api/tags")) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    if (-not (Wait-Ollama)) {
      throw "Ollama did not become reachable on http://127.0.0.1:11434."
    }
  }

  Write-GeneratedModelfile
  $installed = Get-OllamaModelNames
  if ($installed -notcontains $env:QWEN_MODEL_TAG) {
    & ollama create $env:QWEN_MODEL_TAG -f $GeneratedModelfile
  }

  $body = @{
    model = $env:QWEN_MODEL_TAG
    stream = $false
    messages = @(
      @{
        role = "user"
        content = "Reply with READY only."
      }
    )
  } | ConvertTo-Json -Depth 8

  Invoke-RestMethod `
    -Uri "http://127.0.0.1:11434/api/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 300 | Out-Null
}

if (-not (Test-Path -LiteralPath $env:QWEN_MODEL_PATH)) {
  throw "Qwen GGUF not found: $($env:QWEN_MODEL_PATH)"
}

$stackPaths = [ordered]@{
  "OpenClaw source" = $env:OPENCLAW_SOURCE_DIR
  "NemoClaw source" = $env:NEMOCLAW_SOURCE_DIR
  "OpenShell source" = $env:OPENSHELL_SOURCE_DIR
}

foreach ($item in $stackPaths.GetEnumerator()) {
  if (-not (Test-Path -LiteralPath $item.Value)) {
    throw "$($item.Key) not found: $($item.Value)"
  }
}

Write-Host "Hackathon root: $Root"
Write-Host "Qwen model:     $($env:QWEN_MODEL_PATH)"
Write-Host "Model tag:      $($env:QWEN_MODEL_TAG)"
Write-Host "OpenClaw src:   $($env:OPENCLAW_SOURCE_DIR)"
Write-Host "NemoClaw src:   $($env:NEMOCLAW_SOURCE_DIR)"
Write-Host "OpenShell src:  $($env:OPENSHELL_SOURCE_DIR)"
Write-Host "OpenClaw cfg:   $($env:OPENCLAW_CONFIG_PATH)"
Write-Host "OpenClaw home:  $($env:OPENCLAW_HOME)"
Write-Host "OpenClaw state: $($env:OPENCLAW_STATE_DIR)"
Write-Host ""

$commands = "openclaw", "ollama", "nemoclaw", "openshell", "docker"
foreach ($command in $commands) {
  $status = if (Test-CommandExists $command) { "found" } else { "missing" }
  Write-Host ("{0,-10} {1}" -f $command, $status)
}

if ($StartModel) {
  Write-Host ""
  Write-Host "Importing and testing Qwen through Ollama..."
  Ensure-OllamaModel
  Write-Host "Ollama model ready: $($env:QWEN_MODEL_TAG)"
}

if ($RunOpenClawCheck) {
  if (-not (Test-CommandExists "openclaw")) {
    throw "openclaw is not on PATH."
  }
  Write-Host ""
  Write-Host "Checking OpenClaw with isolated config..."
  & openclaw --version
  & openclaw models list --provider ollama
}

if ($RunNemoClawOnboard) {
  if (-not (Test-CommandExists "nemoclaw")) {
    throw "nemoclaw is not on PATH. Install NemoClaw first or run the installer from D:\models\nemoclaw-installer.sh in a Linux/WSL shell."
  }
  if (-not (Test-CommandExists "openshell")) {
    throw "openshell is not on PATH. NemoClaw needs OpenShell available or installable during onboarding."
  }
  Write-Host ""
  Write-Host "Running NemoClaw onboarding for sandbox '$($env:NEMOCLAW_SANDBOX_NAME)'..."
  & nemoclaw onboard --non-interactive --yes
}
