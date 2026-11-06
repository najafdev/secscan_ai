#!/bin/bash
# OpenOS First Boot Configuration
# Runs on the first boot to finalize system setup

set -e

FIRST_BOOT_FLAG="$HOME/.config/openos/.first-boot-done"

if [ -f "$FIRST_BOOT_FLAG" ]; then
    exit 0
fi

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║                                               ║"
echo "║     ⚡ Welcome to OpenOS!                     ║"
echo "║     Your AI Operating System                  ║"
echo "║                                               ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

# Ensure config directories exist
mkdir -p ~/.config/openos
mkdir -p ~/.local/share/openos
mkdir -p ~/.cache/openos

# Copy default config if not present
if [ ! -f ~/.config/openos/config.toml ]; then
    cp /etc/skel/.config/openos/config.toml ~/.config/openos/config.toml 2>/dev/null || true
fi

# ── AI Backend Setup ──
# Check if backend is already configured
OPENOS_BACKEND=$(grep -oP 'backend\s*=\s*"\K[^"]+' ~/.config/openos/config.toml 2>/dev/null || echo "")

if [ -z "$OPENOS_BACKEND" ]; then
    echo "🧠 Let's set up your AI engine..."
    echo ""

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SETUP_SCRIPT="${SCRIPT_DIR}/setup-backend.sh"

    # Try multiple locations for the setup script
    if [ -f "$SETUP_SCRIPT" ]; then
        bash "$SETUP_SCRIPT"
    elif [ -f "/opt/openos/scripts/setup-backend.sh" ]; then
        bash /opt/openos/scripts/setup-backend.sh
    elif command -v openos-setup-backend &>/dev/null; then
        openos-setup-backend
    else
        echo "⚠️  Backend setup script not found."
        echo "   Configure later: edit ~/.config/openos/config.toml"
    fi
else
    echo "✅ AI backend already configured: $OPENOS_BACKEND"
fi

echo ""
echo "✅ OpenOS is ready!"
echo ""
echo "💡 Quick start:"
echo "   • Type 'openos' to open the AI Shell"
echo "   • Type 'openos \"help\"' for examples"
echo "   • Press Super+A for the AI Assistant"
echo "   • Press Super+Enter for the OpenOS Terminal"
echo ""
echo "🔧 Change AI backend anytime:"
echo "   • Run: openos-setup-backend"
echo "   • Or in OpenOS Shell: backend ollama / backend api / backend copilot"
echo ""

# Mark first boot as done
touch "$FIRST_BOOT_FLAG"
