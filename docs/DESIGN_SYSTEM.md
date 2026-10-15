# Design System

Single source: [`design/tokens.json`](../design/tokens.json) (light and dark themes, type, spacing, radius, shadow). Light values are lifted from `build_presentation.py`; dark values come from the Databricks terminal theme in the sibling interview repo or are derived, and say so in their `usage` notes.

## Rules

- Headings in `accent-navy`; body in `ink-body` on `bg`; secondary text in `ink-muted`. Never use `ink-faint`, `accent-amber`, `accent-green` or `accent-gold` for text on white: they measure 2.56, 3.19, 3.30 and 2.94 to 1 (WCAG needs 4.5 for body text).
- Medallion layers use the `medallion-*` tokens: Bronze copper, Silver slate, Gold yellow. The older `tier-bronze-*` and `tier-gold-*` pill colours (`#fef3c7`, `#fef9c3`) are almost the same yellow; do not use them to tell the layers apart.
- Serving is blue. Cross-cutting controls are a dashed `accent-navy` outline, never a fifth layer colour.
- Every diagram node carries a name (mono, `node-name`) and one line (`node-sub`). Arrows run between layers, not between every table; per-table lineage lives in `assets/architecture_diagram.md`.
- Show one status or layer by colour **and** a word. Panels carry their layer label.

## Regenerate the architecture diagram

```bash
python3 scripts/render_architecture.py   # writes assets/architecture-light.svg and -dark.svg
```

Change a colour in `design/tokens.json`, rerun, commit both. The README picks the right file with `<picture>`.
