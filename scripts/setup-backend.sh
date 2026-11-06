#!/bin/bash
# OpenOS AI Backend Setup Script
# Can be run standalone or called from first-boot.sh
#
# Usage:
#   openos-setup-backend          # Interactive wizard
#   openos-setup-backend ollama   # Direct Ollama setup
#   openos-setup-backend api      # Direct OpenAI API setup
#   openos-setup-backend copilot  # Direct copilot-api setup

set -e

OPENOS_CONFIG_DIR="${HOME}/.config/openos"
OPENOS_CONFIG_FILE="${OPENOS_CONFIG_DIR}/config.toml"

# ── Helpers ──

ensure_config_dir() {
    mkdir -p "$OPENOS_CONFIG_DIR"
}

write_backend_config() {
    local backend="$1"
    local host="$2"
    local model="$3"
    local api_key="$4"

    ensure_config_dir

    # If config exists, update the [llm] section; otherwise create it
    if [ -f "$OPENOS_CONFIG_FILE" ]; then
        # Use a temp file to replace the llm section
        python3 -c "
import toml, sys
try:
    cfg = toml.load('$OPENOS_CONFIG_FILE')
except:
    cfg = {}
cfg.setdefault('llm', {})
cfg['llm']['backend'] = '$backend'
cfg['llm']['host'] = '$host'
cfg['llm']['default_model'] = '$model'
if '$api_key':
    cfg['llm']['api_key'] = '$api_key'
with open('$OPENOS_CONFIG_FILE', 'w') as f:
    toml.dump(cfg, f)
print('Config updated.')
" 2>/dev/null || {
            # Fallback: write minimal config if python fails
            cat > "$OPENOS_CONFIG_FILE" << TOML
[llm]
backend = "$backend"
host = "$host"
default_model = "$model"
api_key = "$api_key"
TOML
        }
    else
        cat > "$OPENOS_CONFIG_FILE" << TOML
[llm]
backend = "$backend"
host = "$host"
default_model = "$model"
api_key = "$api_key"
temperature = 0.3
max_tokens = 2048
timeout = 120
auto_upgrade = true

[shell]
prompt_symbol = "openos>"
show_thinking = false
confirm_destructive = true
history_size = 1000
color_theme = "dark"

[daemon]
enabled = true
monitor_interval = 30
proactive_enabled = true

[modules]
enabled = [
    "file_manager",
    "system_maintenance",
    "app_launcher",
    "window_manager",
    "package_manager",
    "media_player",
    "web_browser",
    "screen_reader",
    "power_manager",
]
TOML
    fi

    echo "✅ Backend configured: $backend → $host (model: $model)"
}

# ── Setup Functions ──

setup_ollama() {
    echo ""
    echo "🧠 Setting up Ollama (Local AI)..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Install Ollama if not present
    if ! command -v ollama &>/dev/null; then
        echo "📦 Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        echo "✅ Ollama installed."
    else
        echo "✅ Ollama is already installed."
    fi

    # Start Ollama service
    if ! pgrep -x ollama >/dev/null; then
        echo "🚀 Starting Ollama..."
        ollama serve &
        sleep 3
    fi

    # Ask which model to pull
    echo ""
    echo "Choose a model:"
    echo "  1) llama3.2:3b   (~2GB, fast, good for most tasks)"
    echo "  2) llama3.2:1b   (~1GB, fastest, lighter tasks)"
    echo "  3) llama3.1:8b   (~4.5GB, best quality)"
    echo "  4) Skip download  (pull a model later with: ollama pull <model>)"
    echo ""
    read -p "Select [1-4, default=1]: " model_choice

    local model="llama3.2:3b"
    case "$model_choice" in
        2) model="llama3.2:1b" ;;
        3) model="llama3.1:8b" ;;
        4) model="" ;;
        *) model="llama3.2:3b" ;;
    esac

    if [ -n "$model" ]; then
        echo ""
        echo "📥 Downloading $model (this may take a few minutes)..."
        ollama pull "$model"
    fi

    write_backend_config "ollama" "http://localhost:11434" "${model:-llama3.2:3b}" ""

    echo ""
    echo "🎉 Ollama is ready! Your AI runs 100% locally."
}

setup_api() {
    echo ""
    echo "☁️  Setting up OpenAI-compatible API..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "This works with: OpenAI, Google Gemini, Groq, Together AI, etc."
    echo ""

    read -p "API Base URL [default: https://api.openai.com]: " api_host
    api_host="${api_host:-https://api.openai.com}"

    read -p "API Key: " api_key
    if [ -z "$api_key" ]; then
        echo "⚠️  No API key provided. You can set it later in ~/.config/openos/config.toml"
    fi

    read -p "Model name [default: gpt-4o]: " model_name
    model_name="${model_name:-gpt-4o}"

    write_backend_config "openai" "$api_host" "$model_name" "$api_key"

    echo ""
    echo "🎉 API backend configured!"
}

setup_copilot() {
    echo ""
    echo "🔌 Setting up copilot-api (Local Proxy)..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Make sure copilot-api is running on your machine."
    echo ""

    read -p "Proxy host [default: http://localhost:4141]: " proxy_host
    proxy_host="${proxy_host:-http://localhost:4141}"

    read -p "Model name [default: gpt-4o]: " model_name
    model_name="${model_name:-gpt-4o}"

    write_backend_config "copilot-api" "$proxy_host" "$model_name" ""

    echo ""
    echo "🎉 Copilot-API backend configured!"
}

# ── Interactive Menu ──

show_menu() {
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║                                                   ║"
    echo "║     ⚡ OpenOS — AI Backend Setup                  ║"
    echo "║                                                   ║"
    echo "╠═══════════════════════════════════════════════════╣"
    echo "║                                                   ║"
    echo "║  Choose your AI backend:                          ║"
    echo "║                                                   ║"
    echo "║  1) 🧠 Ollama      (local, private, ~2GB)         ║"
    echo "║  2) ☁️  OpenAI API   (cloud, needs API key)        ║"
    echo "║  3) 🔌 Copilot-API (local proxy)                  ║"
    echo "║  4) ⏭️  Skip         (configure later)             ║"
    echo "║                                                   ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo ""
    read -p "Select [1-4]: " choice

    case "$choice" in
        1) setup_ollama ;;
        2) setup_api ;;
        3) setup_copilot ;;
        4)
            echo ""
            echo "⏭️  Skipped. Configure later with: openos-setup-backend"
            echo "   Or edit: ~/.config/openos/config.toml"
            # Write minimal config with empty backend
            write_backend_config "" "http://localhost:11434" "llama3.2:3b" ""
            ;;
        *)
            echo "Invalid choice. Please try again."
            show_menu
            ;;
    esac
}

# ── Main Entry ──

case "${1:-}" in
    ollama)  setup_ollama ;;
    api)     setup_api ;;
    copilot) setup_copilot ;;
    "")      show_menu ;;
    *)
        echo "Usage: openos-setup-backend [ollama|api|copilot]"
        echo ""
        echo "  ollama   — Install & configure Ollama (local AI)"
        echo "  api      — Configure OpenAI-compatible cloud API"
        echo "  copilot  — Configure copilot-api local proxy"
        echo ""
        echo "Run without arguments for interactive setup."
        exit 1
        ;;
esac
