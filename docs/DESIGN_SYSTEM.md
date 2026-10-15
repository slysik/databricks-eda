# Design System

Single source: [`design/tokens.json`](../design/tokens.json) (light and dark themes, type, spacing, radius, shadow). Light values are lifted from `build_presentation.py`; dark values come from the Databricks terminal theme in the sibling interview repo or are derived, and say so in their `usage` notes.

## Rules

- Headings in `accent-navy`; body in `ink-body` on `bg`; secondary text in `ink-muted`. Never use `ink-faint`, `accent-amber`, `accent-green` or `accent-gold` for text on white: they measure 2.56, 3.19, 3.30 and 2.94 to 1 (WCAG needs 4.5 for body text).
- Medallion layers use the `medallion-*` tokens: Bronze copper, Silver slate, Gold yellow. The older `tier-bronze-*` and `tier-gold-*` pill colours (`#fef3c7`, `#fef9c3`) are almost the same yellow; do not use them to tell the layers apart.
- Diagram style: white `surface` cards with a soft shadow on `bg`, thin `ink-muted` connectors with a small `brand-orange` dot at each start, and one large pipeline card holding the Bronze, Silver and Gold cylinders (`medallion-*`). Governance and quality sit in one panel above the flow, never as a fifth layer colour.
- Each card carries a name (`node-name`, mono for tables) and one line (`node-sub`). Arrows run between stages, not between every table; per-table lineage lives in `assets/architecture_diagram.md`.
- Show a status or layer by colour **and** a word. Cylinders carry their layer label.

## Regenerate the architecture diagram

```bash
python3 scripts/render_architecture.py   # writes assets/architecture-light.svg and -dark.svg
```

Change a colour in `design/tokens.json`, rerun, commit both. The README picks the right file with `<picture>`.
