# 🚀 OpenOS v0.3.0 Release Notes

We are excited to release **OpenOS v0.3.0**! This release marks a complete rebranding and package refactoring, along with major code quality updates, brand assets, community resources, and a new public landing website.

---

## 🌟 What's New in v0.3.0

### 🔄 Project Rebranding & Package Refactoring
- Completely renamed the project from `sai-os` / `sai` to **`OpenOS`**.
- Refactored all core directory layouts and python packages:
  - `sai_core` ➔ `openos_core`
  - `sai_desktop` ➔ `openos_desktop`
  - `sai_installer` ➔ `openos_installer`
- Updated all python import structures, command entry points, and global configuration directories to map to `openos`.

### 🎨 Brand Logo Integration
- Integrated the new OpenOS logo across multiple visual components:
  - **README.md** header decoration.
  - **Installer UI** sidebar branding layout.
  - **AI Assistant Window** header bar.
  - **Desktop Panel** brand indicator.

### 🌐 Landing Page & GitHub Pages
- Created a modern responsive landing page in `website/`:
  - Features an interactive **Terminal Simulator** cycle demonstrating live system maintenance, app launching, and media player operations.
  - Deployed static pages hosting directly from the repository's `gh-pages` branch.

### 🛡️ Code Quality & Type Safety
- Addressed all static type errors across the entire codebase of 55 source files using `mypy` and `ruff`.
- Resolved compatibility warnings for compiler operations on Python 3.14.

### 📄 Community & Governance Files
- Added formal repository documents:
  - **LICENSE**: Official GPL-3.0 copy.
  - **CONTRIBUTING.md**: Contributor instructions and environment setups.
  - **CONTRIBUTORS.md**: Project credit directory.
  - **SECURITY.md**: Security vulnerabilities private reporting channel.
  - **CODE_OF_CONDUCT.md**: Contributor Covenant code.
  - **Templates**: Pull Request and Bug Report/Feature Request templates.
  - **donate.md**: Sponsorship and donation inquiries guide.

---

## 💻 Installation

```bash
git clone https://github.com/yashab-cyber/sai-os.git
cd sai-os
make install-all
make setup-ollama
make run-shell
```

Thank you to the community and Yashab Alam for steering the project! 🚀
