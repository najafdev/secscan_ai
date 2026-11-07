# 10. Troubleshooting

Common issues and their solutions.

---

## Installation Issues

### "Python not found" or "Python 3.9+ required"

HackBot requires Python 3.9 or newer.

```bash
# Check version
python3 --version

# Install on Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv

# Install on macOS
brew install python3

# Install on Windows
# Download from https://www.python.org/downloads/
# Check "Add Python to PATH" during installation
```

### "hackbot: command not found"

The `hackbot` script may not be in your PATH.

```bash
# Add user bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### pip install fails

```bash
# Upgrade pip first
python3 -m pip install --upgrade pip

# Try with --user flag
python3 -m pip install --user "hackbot @ git+https://github.com/yashab-cyber/hackbot.git"

# Or use pipx for isolated install
pipx install "hackbot[all] @ git+https://github.com/yashab-cyber/hackbot.git"
```

### PDF report: "reportlab not installed"

```bash
pip install hackbot[pdf]
# or
pip install reportlab matplotlib Pillow
```

### GUI: "pywebview not installed"

```bash
pip install hackbot[gui]
# or
pip install flask pywebview
```

---

## API Key Issues

### "API key is invalid"

- Double-check the key is correct and not expired
- Ensure you're using the right key for the selected provider
- Check if your account has billing/credits enabled
- Verify the provider service is online

### Key works for provider X but not provider Y

Each provider has its own key format. Make sure you're setting the key for the correct provider:

```
/provider openai
/key sk-...          # OpenAI key

/provider anthropic
/key sk-ant-...       # Anthropic key
```

### "Connection error" or timeout

- Check your internet connection
- Verify the provider's status page
- For Ollama/local: ensure the server is running
- Try setting a custom base URL if behind a proxy

---

## Agent Issues

### "No tools found"

Install security tools:

```bash
# Linux (Ubuntu/Debian)
sudo apt install nmap nikto dirb hydra curl wget

# Full install with security tools
./install.sh full

# Check what's available
hackbot tools
```

### Agent gets stuck in a loop

```
/stop                         # Stop the agent
/step "Try a different approach"  # Guide it manually
```

Or adjust max steps in config to limit iterations.

### "Command blocked by safe mode"

Safe mode prevents destructive operations. To allow:

```
# Temporarily disable
hackbot --no-safe-mode

# Or in REPL config
# Set safe_mode: false in ~/.config/hackbot/config.yaml
```

⚠️ Only disable safe mode in authorized test environments.

---

## GUI Issues

### GUI doesn't launch

If you start HackBot GUI with `sudo`, desktop GUI backends (pywebview/GTK/WebKit)
often cannot access your user display/session.

Use this pattern instead:

```bash
# 1) Cache sudo credentials (optional, for privileged scans later)
sudo -v

# 2) Launch GUI as normal user (not sudo)
hackbot gui
```

If you need elevated tool execution in agent mode, keep GUI non-root and enable
HackBot sudo mode (`hackbot --sudo` or Settings -> sudo mode).

Do not use `sudo -v hackbot gui`.
Use `sudo -v && hackbot gui`.

```bash
# Check dependencies
pip install flask pywebview

# Try with specific host/port
hackbot gui --host 127.0.0.1 --port 8080

# Check if port is in use
lsof -i :1337
```

### GUI fallback shows "QT cannot be loaded" / "No module named qtpy"

Install Qt backend inside your virtual environment:

```bash
pip install PyQt5 qtpy
```

Then retry:

```bash
hackbot gui
```

### GUI fallback shows "GTK cannot be loaded" / "No module named gi"

Install GTK Python bindings from system packages (Debian/Kali/Ubuntu):

```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

Important: `gi` is usually a system Python module. If HackBot runs inside a venv,
your venv may not see `gi` unless it was created with system site packages:

```bash
python3 -m venv --system-site-packages hackbot
source hackbot/bin/activate
```

Alternative: use the Qt backend (`pip install PyQt5 qtpy`) instead of GTK in venv.

### GUI shows "Loading..." forever

- Check the terminal for error messages
- Verify your API key is set
- Try refreshing the page (if in browser mode)

### Blank or broken GUI

```bash
# Reinstall GUI dependencies
pip install --force-reinstall flask pywebview
```

---

## Session Issues

### "Session not found"

```
/sessions                     # List all available sessions
/load                         # Shows a list of sessions to pick from
```

Session IDs follow the format `{mode}_{timestamp}`. You can use a partial match.

### Sessions taking too much disk space

Sessions are in `~/.local/share/hackbot/sessions/`. Delete old ones:

```bash
# In REPL
/load                         # List sessions
# Then delete from Sessions panel in GUI

# Manually
rm ~/.local/share/hackbot/sessions/old_session.json
```

---

## Performance Issues

### Slow responses

- Switch to a faster provider (Groq is ultra-fast)
- Use a smaller model (`gpt-4o-mini`, `llama-3.1-8b-instant`)
- Reduce `max_tokens` in config
- For local models: ensure GPU acceleration is enabled

### High memory usage

- Conversation summarization kicks in automatically
- Use `/clear` to reset conversation if not needed
- Close unused GUI panels

---

## Proxy Issues

### "Address already in use"

```
/proxy start 9090             # Use a different port
# Or kill the process on port 8080
lsof -ti :8080 | xargs kill
```

### No traffic captured

- Verify your tool/browser is using the correct proxy address
- Check the scope: `/proxy scope clear` to remove domain restrictions
- Ensure the proxy is running: `/proxy status`

---

## Getting Help

- **In HackBot**: `/help` shows all commands
- **Manual**: `/manual` opens this documentation
- **GitHub Issues**: [github.com/yashab-cyber/hackbot/issues](https://github.com/yashab-cyber/hackbot/issues)
- **Contact**: yashabalam707@gmail.com or yashabalam9@gmail.com

---

## Reporting Bugs

Include the following when reporting issues:

1. HackBot version (`/version`)
2. Operating system
3. Python version (`python3 --version`)
4. Provider and model being used
5. Steps to reproduce
6. Error message or traceback (run with `--verbose` for details)

File issues at: [github.com/yashab-cyber/hackbot/issues](https://github.com/yashab-cyber/hackbot/issues)

---

**Developed by [Yashab Alam](https://github.com/yashab-cyber)**
[GitHub](https://github.com/yashab-cyber) · [LinkedIn](https://www.linkedin.com/in/yashab-alam) · [Donate](../DONATE.md)
