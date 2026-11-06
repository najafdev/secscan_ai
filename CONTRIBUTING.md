# 🤝 Contributing to OpenOS

Thank you for your interest in contributing to **OpenOS**! Contributions from the community help make this project better for everyone. Please read through this guide to understand how you can participate.

---

## 🚀 How to Get Started

1. **Fork the Repository**: Create your own copy of the repository on GitHub.
2. **Clone Locally**:
   ```bash
   git clone https://github.com/your-username/sai-os.git
   cd sai-os
   ```
3. **Set Up Development Environment**:
   ```bash
   make install-all
   ```
4. **Create a Branch**: Create a feature branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 🛠️ Code Style & Guidelines

* **Python**: We follow standard PEP 8 formatting. Run `ruff` to verify your formatting before submitting:
  ```bash
  make format
  make lint
  ```
* **Type Annotations**: Ensure your code is fully annotated. Verify static type checks pass with `mypy`:
  ```bash
  mypy openos_core/ openos_desktop/ openos_installer/ --ignore-missing-imports
  ```
* **Git Commit Messages**: Keep your commit messages clear, descriptive, and in the imperative mood (e.g. `Fix window positioning bug`, `Add speech-to-text module`).

---

## 🐛 Reporting Bugs & Requesting Features

* Use the **GitHub Issues** tab to report bugs or suggest new features.
* Provide as much context as possible, including your OS version, Python version, log outputs, and steps to reproduce the issue.

---

## 📬 Submitting Pull Requests

1. Commit and push your changes to your fork.
2. Submit a Pull Request (PR) to the `master` branch of the main repository.
3. Provide a clear description of your changes, what issues they address, and how they were tested.

Thank you for contributing! 🚀
