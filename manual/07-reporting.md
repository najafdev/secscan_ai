# 7. Reporting

HackBot generates professional security assessment reports in 4 formats.

---

## Report Formats

| Format | Extension | Best for |
|--------|-----------|----------|
| **HTML** | `.html` | Sharing with stakeholders, professional presentation |
| **Markdown** | `.md` | Git-friendly, easy editing, documentation |
| **JSON** | `.json` | Integration with other tools, automation |
| **PDF** | `.pdf` | Formal delivery, executive reporting |

---

## Generating Reports

### CLI
```
/export html                  # Export as HTML
/export markdown              # Export as Markdown
/export json                  # Export as JSON
/export                       # Uses default format from config
/pdf                          # Generate PDF report
```

### GUI
In the **Agent** panel, use the Export buttons (HTML, Markdown, JSON, PDF).

### Terminal
Reports are auto-generated after `hackbot agent` completes.

---

## Report Contents

Every report includes:

| Section | Description |
|---------|-------------|
| **Header** | Target, date, scope, duration |
| **Executive Summary** | Severity overview with counts (Critical/High/Medium/Low/Info) |
| **Findings** | Each finding with severity badge, title, description, evidence, recommendation |
| **Tool Execution Log** | Every tool run: command, success/failed, duration, exit code |
| **Raw Output** | Optional raw tool output (configurable via `include_raw_output`) |

### PDF Report (Additional Sections)
| Section | Description |
|---------|-------------|
| **Cover Page** | Professional cover with HackBot branding |
| **Risk Matrix** | Visual chart showing severity distribution |
| **Compliance Mapping** | Auto-included if findings exist (PCI DSS, NIST, OWASP, ISO 27001) |
| **Charts** | Severity bar chart and distribution pie chart |

---

## Report Storage

Reports are saved to:
```
~/.local/share/hackbot/reports/
```

File naming convention:
```
hackbot_report_<target>_<timestamp>.<format>
```

---

## Configuration

```
/config
```

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `report_format` | `html`, `markdown`, `json` | `html` | Default export format |
| `auto_save` | `true`/`false` | `true` | Auto-save reports after assessments |
| `include_raw_output` | `true`/`false` | `true` | Include raw tool output |

---

## PDF Requirements

PDF reports require the `reportlab` package:

```bash
pip install hackbot[pdf]
# or
pip install reportlab matplotlib Pillow
```

---

## Campaign Reports

For multi-target campaigns, `/campaign report` generates an aggregate report containing:
- Campaign overview (name, targets, duration)
- Per-target findings summary
- Cross-target finding comparison
- Aggregate severity statistics

---

Next: [Memory & Sessions →](08-memory-sessions.md)
