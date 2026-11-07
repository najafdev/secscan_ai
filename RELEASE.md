# HackBot — Release Guide

Step-by-step instructions for creating a GitHub release for HackBot.

---

## Prerequisites

- **GitHub CLI** (`gh`) installed and authenticated
- Push access to `yashab-cyber/hackbot`
- All changes committed and pushed to `main`

```bash
# Verify gh is authenticated
gh auth status

# Verify you're on main with no uncommitted changes
git status
```

---

## Step 1: Update the Version Number

Edit the version in **two files**:

| File | Field |
|------|-------|
| `hackbot/__init__.py` | `__version__ = "X.Y.Z"` |
| `pyproject.toml` | `version = "X.Y.Z"` |

**Versioning convention:** `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking changes (2.0.0)
- **MINOR** — new features (1.1.2)
- **PATCH** — bug fixes (1.0.1)

```bash
# Example: bump to 1.1.2
sed -i 's/__version__ = ".*"/__version__ = "1.1.2"/' hackbot/__init__.py
sed -i 's/^version = ".*"/version = "1.1.2"/' pyproject.toml
```

Commit the version bump:

```bash
git add hackbot/__init__.py pyproject.toml
git commit -m "chore: bump version to 1.1.2"
git push origin main
```

---

## Step 2: Create a Git Tag

```bash
# Create an annotated tag
git tag -a v1.1.2 -m "Release v1.1.2"

# Push the tag to GitHub
git push origin v1.1.2
```

---

## Step 3: Create the GitHub Release

### Option A: Using GitHub CLI (Recommended)

```bash
gh release create v1.1.2 \
  --title "HackBot v1.1.2" \
  --notes "## What's New

- Feature 1 description
- Feature 2 description

## Bug Fixes

- Fix 1 description

## Full Changelog
https://github.com/yashab-cyber/hackbot/compare/v1.1.1...v1.1.2"
```

### Option B: With Release Notes from a File

Create a temporary release notes file:

```bash
cat > /tmp/release-notes.md << 'EOF'
## What's New

- Added TinyLlama support for low-end PCs
- Added xploiter/pentester cybersecurity model
- Added Ollama & Local model usage guides
- Added screenshots to README

## Bug Fixes

- Fixed screenshot labels in README

## Full Changelog
https://github.com/yashab-cyber/hackbot/compare/v1.1.1...v1.1.2
EOF

gh release create v1.1.2 \
  --title "HackBot v1.1.2" \
  --notes-file /tmp/release-notes.md
```

### Option C: Auto-Generate Notes from Commits

```bash
gh release create v1.1.2 \
  --title "HackBot v1.1.2" \
  --generate-notes
```

This automatically generates release notes from commit messages and pull requests since the last release.

### Option D: Upload Artifacts with the Release

If you have build artifacts (wheels, archives, etc.):

```bash
# Build the package first
pip install build
python -m build   # creates dist/hackbot-1.1.2.tar.gz and .whl

# Create release with attachments
gh release create v1.1.2 \
  --title "HackBot v1.1.2" \
  --generate-notes \
  dist/hackbot-1.1.2.tar.gz \
  dist/hackbot-1.1.2-py3-none-any.whl
```

---

## Step 4: Verify the Release

```bash
# List releases
gh release list

# View the release
gh release view v1.1.2

# Open in browser
gh release view v1.1.2 --web
```

---

## Quick One-Liner (All Steps Combined)

For a fast release after everything is committed and pushed:

```bash
VERSION="1.1.2" && \
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" hackbot/__init__.py && \
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml && \
git add -A && \
git commit -m "chore: bump version to $VERSION" && \
git push origin main && \
git tag -a "v$VERSION" -m "Release v$VERSION" && \
git push origin "v$VERSION" && \
gh release create "v$VERSION" --title "HackBot v$VERSION" --generate-notes
```

---

## Deleting a Release (If Needed)

```bash
# Delete the release (keeps the tag)
gh release delete v1.1.2 --yes

# Delete the tag too
git tag -d v1.1.2
git push --delete origin v1.1.2
```

---

## Draft Releases (Review Before Publishing)

Create as draft, review on GitHub, then publish:

```bash
gh release create v1.1.2 \
  --title "HackBot v1.1.2" \
  --generate-notes \
  --draft
```

Then go to **GitHub → Releases → Edit → Publish**.

---

## Pre-release (Beta / RC)

```bash
gh release create v2.0.0-beta.1 \
  --title "HackBot v2.0.0 Beta 1" \
  --generate-notes \
  --prerelease
```

---

## Release Notes Template

Use this template when writing manual release notes:

```markdown
## 🚀 What's New
- **Feature Name** — Brief description (#PR)

## 🐛 Bug Fixes
- Fixed description (#PR)

## 📖 Documentation
- Updated docs for X

## ⚠️ Breaking Changes
- Description of breaking change (if any)

## 📦 Installation
\```bash
pip install "hackbot @ git+https://github.com/yashab-cyber/hackbot.git"
\```

## Full Changelog
https://github.com/yashab-cyber/hackbot/compare/vOLD...vNEW
```

---

## Creating Your First Release (v1.0.0)

Since HackBot doesn't have any releases yet, run this to create the initial release:

```bash
cd /path/to/hackbot

# Tag the current state as v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0 — Initial production release"
git push origin v1.0.0

# Create the GitHub release
gh release create v1.0.0 \
  --title "HackBot v1.0.0 — Initial Release" \
  --notes "## 🎉 HackBot v1.0.0 — Initial Production Release

### Features
- 🤖 **Agent Mode** — Autonomous penetration testing with real tools
- 💬 **Chat Mode** — Interactive cybersecurity Q&A with memory
- 📋 **Plan Mode** — 8 structured pentest plan templates
- 🖥️ **Native Desktop GUI** — pywebview-powered dark theme interface
- 🛡️ **CVE/Exploit Lookup** — Real-time NVD search + GitHub PoC discovery
- 🌐 **OSINT Module** — Subdomains, DNS, WHOIS, tech stack, emails
- 🗺️ **Network Topology** — Interactive D3.js network visualization
- 📋 **Compliance Mapping** — PCI DSS, NIST 800-53, OWASP Top 10, ISO 27001
- 🔀 **Diff Reports** — Compare assessments (new/fixed/persistent findings)
- 🎯 **Multi-Target Campaigns** — Coordinated multi-host assessments
- 🧩 **Custom Plugins** — Python plugin system for custom tools
- 🔧 **AI Remediation** — Auto-generate fix commands and config patches
- 🔌 **HTTP Proxy** — Intercepting proxy with traffic capture and replay
- 🧠 **Memory & Sessions** — Auto-save, session history, conversation summarization
- 🌍 **10 AI Providers** — OpenAI, Anthropic, Gemini, Groq, Mistral, DeepSeek, Together, OpenRouter, Ollama, Local
- 🔧 **30+ Tool Integrations** — nmap, nikto, sqlmap, nuclei, ffuf, hydra, and more
- 📊 **Reports** — HTML, Markdown, JSON, and professional PDF reports
- 💻 **Cross-Platform** — Linux, macOS, Windows

### Installation
\`\`\`bash
pip install \"hackbot @ git+https://github.com/yashab-cyber/hackbot.git\"
\`\`\`

### Local Models (No API Key)
\`\`\`bash
ollama pull xploiter/pentester
hackbot --provider ollama --model xploiter/pentester
\`\`\`
"
```

---

**Author:** Yashab Alam  
**Repository:** [github.com/yashab-cyber/hackbot](https://github.com/yashab-cyber/hackbot)
