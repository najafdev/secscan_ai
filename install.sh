#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# HackBot — Universal Installer for Linux & macOS
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

VERSION="1.2.4"
REPO="yashab-cyber/hackbot"
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

banner() {
    echo -e "${GREEN}"
    echo "  ╦ ╦╔═╗╔═╗╦╔═╔╗ ╔═╗╔╦╗"
    echo "  ╠═╣╠═╣║  ╠╩╗╠╩╗║ ║ ║ "
    echo "  ╩ ╩╩ ╩╚═╝╩ ╩╚═╝╚═╝ ╩ "
    echo -e "${NC}"
    echo -e "${CYAN}  AI Cybersecurity Assistant — Installer v${VERSION}${NC}"
    echo -e "  ─────────────────────────────────────────────"
    echo -e "  ${BOLD}Developed by Yashab Alam${NC}"
    echo -e "  GitHub:   ${CYAN}https://github.com/yashab-cyber${NC}"
    echo -e "  LinkedIn: ${CYAN}https://www.linkedin.com/in/yashab-alam${NC}"
    echo -e "  Email:    yashabalam707@gmail.com | yashabalam9@gmail.com"
    echo -e "  ─────────────────────────────────────────────"
    echo -e "  ${RED}❤️  Support HackBot → https://github.com/yashab-cyber/hackbot/blob/main/DONATE.md${NC}"
    echo ""
}

info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Detect OS ────────────────────────────────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Linux*)   OS="linux";;
        Darwin*)  OS="macos";;
        CYGWIN*|MINGW*|MSYS*) OS="windows";;
        *)        error "Unsupported OS: $(uname -s)";;
    esac

    case "$(uname -m)" in
        x86_64|amd64)  ARCH="amd64";;
        aarch64|arm64) ARCH="arm64";;
        *)             ARCH="$(uname -m)";;
    esac

    info "Detected: ${OS} (${ARCH})"
}

# ── Check Python ─────────────────────────────────────────────────────────────
check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON="python3"
    elif command -v python &>/dev/null; then
        PYTHON="python"
    else
        error "Python 3.9+ is required. Install it first:
  Linux:  sudo apt install python3 python3-pip python3-venv
  macOS:  brew install python3
  Or:     https://www.python.org/downloads/"
    fi

    PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
        error "Python 3.9+ required, found $PY_VERSION"
    fi

    success "Python $PY_VERSION found ($PYTHON)"
}

# ── Install via pip ──────────────────────────────────────────────────────────
install_pip() {
    info "Installing HackBot via pip..."

    local EXTRAS="[all]"
    if [ "${INSTALL_GUI:-false}" = "true" ]; then
        EXTRAS="[all]"
    fi

    # Try pipx first (isolated install)
    if command -v pipx &>/dev/null; then
        info "Using pipx for isolated installation..."
        pipx install "hackbot${EXTRAS} @ git+https://github.com/${REPO}.git" || {
            warn "pipx install failed, falling back to pip..."
            $PYTHON -m pip install --user "hackbot${EXTRAS} @ git+https://github.com/${REPO}.git"
        }
    else
        $PYTHON -m pip install --user "hackbot${EXTRAS} @ git+https://github.com/${REPO}.git"
    fi

    success "HackBot installed!"
}

# ── Install from local source ────────────────────────────────────────────────
install_local() {
    info "Installing HackBot from local source..."

    # Check if we're in the hackbot repo
    if [ -f "pyproject.toml" ] && grep -q "hackbot" pyproject.toml 2>/dev/null; then
        if [ "${INSTALL_GUI:-false}" = "true" ]; then
            $PYTHON -m pip install --user -e ".[all,dev]"
        else
            $PYTHON -m pip install --user -e ".[all]"
        fi
        success "HackBot installed in development mode!"
    else
        error "Not in the hackbot repository. Run this from the project root."
    fi
}

# ── Install security tools ──────────────────────────────────────────────────
install_security_tools() {
    echo ""
    info "Installing common security tools..."

    # Check if we can use sudo (needed for system package managers)
    if [ "$(id -u)" -ne 0 ]; then
        if ! command -v sudo &>/dev/null; then
            warn "sudo not found and not running as root — skipping system packages"
            warn "Install manually: nmap nikto hydra john curl wget openssl"
            return 0
        fi
        # Validate sudo access; prompt once so individual commands don't re-ask
        info "Root privileges required for system packages (sudo)..."
        if ! sudo -v 2>/dev/null; then
            warn "Could not obtain sudo privileges — skipping system packages"
            warn "Install manually or re-run as root: sudo $0 tools-only"
            return 0
        fi
    else
        # Already root — alias sudo to empty so commands work unchanged
        sudo() { "$@"; }
    fi

    if [ "$OS" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq \
                nmap nikto dirb hydra john whatweb \
                dnsutils whois traceroute netcat-openbsd \
                curl wget openssl sslscan \
                2>/dev/null || warn "Some packages may not be available"
            success "APT packages installed"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y \
                nmap nikto hydra john \
                bind-utils whois traceroute nmap-ncat \
                curl wget openssl \
                2>/dev/null || warn "Some packages may not be available"
            success "DNF packages installed"
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm \
                nmap nikto hydra john \
                bind-tools whois traceroute gnu-netcat \
                curl wget openssl \
                2>/dev/null || warn "Some packages may not be available"
            success "Pacman packages installed"
        fi

        # Install Go-based tools
        if command -v go &>/dev/null; then
            info "Installing Go-based security tools..."
            go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null && success "nuclei installed" || warn "nuclei install failed"
            go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null && success "subfinder installed" || warn "subfinder install failed"
            go install github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null && success "httpx installed" || warn "httpx install failed"
            go install github.com/ffuf/ffuf/v2@latest 2>/dev/null && success "ffuf installed" || warn "ffuf install failed"
        else
            warn "Go not found — skipping nuclei, subfinder, httpx, ffuf"
            info "Install Go: https://go.dev/dl/"
        fi

    elif [ "$OS" = "macos" ]; then
        if command -v brew &>/dev/null; then
            brew install nmap nikto hydra john-jumbo \
                curl wget openssl \
                2>/dev/null || warn "Some brew packages may not be available"
            success "Homebrew packages installed"
        else
            warn "Homebrew not found. Install from https://brew.sh"
        fi
    fi
}

# ── Desktop Shortcut ─────────────────────────────────────────────────────────
install_desktop_shortcut() {
    if [ "${INSTALL_GUI:-false}" != "true" ]; then
        return
    fi

    if [ "$OS" = "linux" ]; then
        info "Creating desktop shortcut..."

        # Find the logo — check local repo first, then installed package
        LOGO_SRC=""
        if [ -f "public/1000023729-removebg-preview.png" ]; then
            LOGO_SRC="public/1000023729-removebg-preview.png"
        fi

        # Install icon
        ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
        mkdir -p "$ICON_DIR"
        if [ -n "$LOGO_SRC" ]; then
            cp "$LOGO_SRC" "$ICON_DIR/hackbot.png"
            success "Icon installed to $ICON_DIR/hackbot.png"
        fi

        # Install .desktop file
        DESKTOP_DIR="$HOME/.local/share/applications"
        mkdir -p "$DESKTOP_DIR"

        cat > "$DESKTOP_DIR/hackbot.desktop" << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=HackBot
GenericName=AI Cybersecurity Assistant
Comment=AI-powered pentesting & cybersecurity assistant with Agent, Chat & Planning modes
Exec=hackbot --gui
Icon=hackbot
Terminal=false
Categories=Security;Network;System;Utility;
Keywords=hacking;pentesting;cybersecurity;security;nmap;ai;
StartupNotify=true
StartupWMClass=hackbot
DESKTOP_EOF

        chmod +x "$DESKTOP_DIR/hackbot.desktop"
        success "Desktop shortcut installed to $DESKTOP_DIR/hackbot.desktop"

        # Update desktop database if available
        if command -v update-desktop-database &>/dev/null; then
            update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        fi

        info "HackBot should now appear in your application menu"

    elif [ "$OS" = "macos" ]; then
        info "On macOS, launch HackBot GUI with: hackbot --gui"
        info "To add to Dock: drag from Applications or create an alias"
    fi
}

# ── Post-install ─────────────────────────────────────────────────────────────
post_install() {
    echo ""

    # Verify installation
    if command -v hackbot &>/dev/null; then
        success "HackBot is ready! Run 'hackbot' to start."
    else
        # Add to PATH hint
        warn "hackbot not found in PATH. You may need to add these to your shell profile:"
        echo ""
        echo "  # Add to ~/.bashrc or ~/.zshrc:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        echo "  Then reload: source ~/.bashrc"
    fi

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          HackBot Installation Complete!          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Quick start:"
    echo "    hackbot                    # Interactive mode"
    echo "    hackbot setup <API_KEY>    # Set your API key"
    echo "    hackbot agent <TARGET>     # Start security testing"
    echo "    hackbot chat               # Chat mode"
    echo "    hackbot plan <TARGET>      # Plan an assessment"
    echo "    hackbot tools              # Check available tools"
    echo "    hackbot --gui              # Launch web GUI"
    echo ""
    echo -e "  ${YELLOW}⚠️  Only test systems you have explicit authorization to test!${NC}"
    echo ""
    echo -e "  ${BOLD}Developed by Yashab Alam${NC}"
    echo -e "  GitHub:   ${CYAN}https://github.com/yashab-cyber${NC}"
    echo -e "  LinkedIn: ${CYAN}https://www.linkedin.com/in/yashab-alam${NC}"
    echo -e "  Email:    yashabalam707@gmail.com | yashabalam9@gmail.com"
    echo -e "  ${RED}❤️  Support: https://github.com/yashab-cyber/hackbot/blob/main/DONATE.md${NC}"
    echo ""
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    banner
    detect_os
    check_python

    MODE="${1:-pip}"

    # Ask about GUI
    echo ""
    echo -e "${BOLD}Interface preference:${NC}"
    echo "  1) CLI only (default)"
    echo "  2) CLI + Web GUI"
    echo ""
    read -rp "Choose [1/2]: " gui_choice
    gui_choice=${gui_choice:-1}

    if [ "$gui_choice" = "2" ]; then
        INSTALL_GUI=true
        info "Will install with GUI support (flask)"
    else
        INSTALL_GUI=false
        info "Installing CLI only"
    fi
    echo ""

    case "$MODE" in
        pip)
            install_pip
            ;;
        local|dev)
            install_local
            ;;
        full)
            install_pip
            install_security_tools
            ;;
        tools-only)
            install_security_tools
            ;;
        *)
            echo "Usage: $0 [pip|local|full|tools-only]"
            echo ""
            echo "  pip         Install HackBot via pip (default)"
            echo "  local       Install from local source (dev mode)"
            echo "  full        Install HackBot + security tools"
            echo "  tools-only  Install only security tools"
            exit 1
            ;;
    esac

    # Install desktop shortcut if GUI was selected
    install_desktop_shortcut

    post_install
}

main "$@"
