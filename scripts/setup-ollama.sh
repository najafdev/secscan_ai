#!/bin/bash
# OpenOS Ollama Setup Script
# Installs Ollama and downloads the default AI model

set -e

echo "🧠 OpenOS — Setting up AI Engine"
echo "================================="

# Check if Ollama is already installed
if command -v ollama &>/dev/null; then
    echo "✅ Ollama is already installed: $(ollama --version)"
else
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✅ Ollama installed."
fi

# Start Ollama service
echo "🚀 Starting Ollama service..."
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo "✅ Ollama is already running."
else
    ollama serve &
    sleep 3
    echo "✅ Ollama started."
fi

# Download default model
echo ""
echo "📥 Downloading AI model (llama3.2:3b — ~2GB)..."
echo "   This may take a few minutes on first run."
ollama pull llama3.2:3b

echo ""
echo "✅ AI Engine is ready!"
echo ""
echo "Test it with: openos \"hello, what can you do?\""
