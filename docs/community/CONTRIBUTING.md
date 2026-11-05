---
title: Contributor Guidelines & Community Playbook
purpose: Guidelines and requirements for contributing code, documentation, and agent models
scope: Open-source contributors, pull request standards, bug triage, and code conventions
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/community/CODE_OF_CONDUCT.md
  - docs/developer/DEVELOPER_GUIDE.md
  - docs/developer/CODING_STANDARDS.md
---

# Contributor Guidelines & Community Playbook

Thank you for your interest in contributing to **AgentDroid**! AgentDroid is an open-source project dedicated to advancing autonomous, privacy-respecting AI operating systems for mobile devices.

---

## 1. Ways to Contribute

* **Core Engineering**: Enhance the multi-agent DAG scheduler, optimize Kotlin coroutines, or expand Compose UI components.
* **Agent Creation**: Build new specialized agents (e.g., Coding Assistant, Travel Coordinator).
* **Provider Integration**: Add support for emerging LLM backends and local inference engines.
* **Documentation**: Improve developer tutorials, write translation guides, or fix technical inaccuracies.
* **Bug Reports & Triage**: Identify edge cases, test on diverse Android OEM skins, and submit reproducible bug reports.

---

## 2. Pull Request Process

1. **Open an Issue First**: Before embarking on large feature work, open an issue to discuss the proposal with maintainers.
2. **Follow Coding Standards**: Ensure code conforms to [Coding Standards](file:///workspaces/hacknova/docs/developer/CODING_STANDARDS.md) and maintains the **Strict Real AI** mandate.
3. **Automated Verification**:
   * All unit tests must pass: `./gradlew testDebugUnitTest`
   * Build must complete cleanly: `./gradlew assembleDebug`
4. **Commit Messages**: Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `perf:`).
5. **Review**: Pull requests require review and sign-off by at least one core maintainer before merging.

---

## Related Documentation
* [Code of Conduct](file:///workspaces/hacknova/docs/community/CODE_OF_CONDUCT.md)
* [Developer Guide](file:///workspaces/hacknova/docs/developer/DEVELOPER_GUIDE.md)
* [Coding Standards](file:///workspaces/hacknova/docs/developer/CODING_STANDARDS.md)
