$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$env:HACKATHON_ROOT = $Root
$env:QWEN_MODEL_PATH = if ($env:QWEN_MODEL_PATH) { $env:QWEN_MODEL_PATH } else { "D:\models\qwen3-30b\Qwen3-30B-A3B-Q4_K_M.gguf" }
$env:QWEN_MODEL_TAG = if ($env:QWEN_MODEL_TAG) { $env:QWEN_MODEL_TAG } else { "qwen3-30b-a3b-local" }
$env:OPENCLAW_SOURCE_DIR = if ($env:OPENCLAW_SOURCE_DIR) { $env:OPENCLAW_SOURCE_DIR } else { "D:\models\openclaw" }
$env:NEMOCLAW_SOURCE_DIR = if ($env:NEMOCLAW_SOURCE_DIR) { $env:NEMOCLAW_SOURCE_DIR } else { "D:\models\NemoClaw" }
$env:OPENSHELL_SOURCE_DIR = if ($env:OPENSHELL_SOURCE_DIR) { $env:OPENSHELL_SOURCE_DIR } else { "D:\models\OpenShell" }

$env:OPENCLAW_HOME = Join-Path $Root ".runtime\openclaw-home"
$env:OPENCLAW_STATE_DIR = Join-Path $Root ".runtime\openclaw-state"
$env:OPENCLAW_CONFIG_PATH = Join-Path $Root "config\openclaw.json"
$env:OLLAMA_API_KEY = if ($env:OLLAMA_API_KEY) { $env:OLLAMA_API_KEY } else { "ollama-local" }

$env:NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE = "1"
$env:NEMOCLAW_NON_INTERACTIVE = "1"
$env:NEMOCLAW_YES = "1"
$env:NEMOCLAW_PROVIDER = if ($env:NEMOCLAW_PROVIDER) { $env:NEMOCLAW_PROVIDER } else { "ollama" }
$env:NEMOCLAW_MODEL = if ($env:NEMOCLAW_MODEL) { $env:NEMOCLAW_MODEL } else { $env:QWEN_MODEL_TAG }
$env:NEMOCLAW_CONTEXT_WINDOW = if ($env:NEMOCLAW_CONTEXT_WINDOW) { $env:NEMOCLAW_CONTEXT_WINDOW } else { "32768" }
$env:NEMOCLAW_SANDBOX_NAME = if ($env:NEMOCLAW_SANDBOX_NAME) { $env:NEMOCLAW_SANDBOX_NAME } else { "vendor-risk-agent" }
$env:NEMOCLAW_POLICY_MODE = if ($env:NEMOCLAW_POLICY_MODE) { $env:NEMOCLAW_POLICY_MODE } else { "suggested" }
$env:NEMOCLAW_POLICY_TIER = if ($env:NEMOCLAW_POLICY_TIER) { $env:NEMOCLAW_POLICY_TIER } else { "balanced" }
