---
title: Feature Request & Agent Proposal Guidelines
purpose: Standard process and templates for proposing new agents, tools, and system features
scope: Community proposals, evaluation criteria, and proposal templates
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/community/ROADMAP.md
  - docs/developer/CUSTOM_AGENT_GUIDE.md
---

# Feature Request & Agent Proposal Guidelines

We welcome proposals for new agents, Android automation actions, and AI provider integrations.

---

## 1. Proposal Evaluation Criteria

When evaluating proposals, maintainers consider:
1. **Security & Privacy**: Does the feature respect user sandboxes? Can it run locally or preserve credential encryption?
2. **Generality**: Does the feature serve a broad segment of Android users, or can it be implemented as a custom agent via the Agent Builder?
3. **No-Fake Policy**: Can the proposed capability run with real, verifiable AI models without simulated data?

---

## 2. Feature Proposal Template

When submitting a feature request on GitHub, please use the following structure:

```markdown
### Summary
Brief 1-2 sentence description of the proposed feature.

### Motivation & Use Case
Why is this feature needed? What problem does it solve for users?

### Proposed Solution
Describe how the feature should behave. Include UI sketches or API signatures if applicable.

### Security & Privacy Impact
Does this require new Android permissions (e.g., Accessibility, Camera, Storage)? How will user data be protected?

### Alternatives Considered
What existing workarounds or tools were evaluated?
```

---

## Related Documentation
* [Community Roadmap](file:///workspaces/hacknova/docs/community/ROADMAP.md)
* [Custom Agent Guide](file:///workspaces/hacknova/docs/developer/CUSTOM_AGENT_GUIDE.md)
