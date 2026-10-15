#!/usr/bin/env python3
"""Render assets/architecture-{light,dark}.svg from design/tokens.json.

Usage: python3 scripts/render_architecture.py        (stdlib only)

Colours come from the token file, so a palette change is one edit plus one run.
The layout is fixed: five layer panels left to right, one controls band below.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOK = {t["name"]: t["value"] for t in json.loads((ROOT / "design/tokens.json").read_text())["color"]["tokens"]}
SANS = json.loads((ROOT / "design/tokens.json").read_text())["type"]["families"]["sans"].replace('"', "'")
MONO = json.loads((ROOT / "design/tokens.json").read_text())["type"]["families"]["mono"].replace('"', "'")

W, H = 1320, 520
PANEL_W, PANEL_Y, NODE_W, NODE_H = 220, 58, 200, 64
COLS = {"source": 40, "bronze": 300, "silver": 560, "gold": 820, "serving": 1080}
SLOT = {0: 104, 1: 204, 2: 304}  # node tops; centres are +32


def render(theme: str) -> str:
    c = lambda n: TOK[n][theme]
    panels = {  # key: (fill, stroke, ink, label)
        "source": (c("surface-muted"), c("ink-muted"), c("ink-body"), "SOURCE"),
        "bronze": (c("medallion-bronze-fill"), c("medallion-bronze-stroke"), c("medallion-bronze-ink"), "BRONZE"),
        "silver": (c("medallion-silver-fill"), c("medallion-silver-stroke"), c("medallion-silver-ink"), "SILVER"),
        "gold": (c("medallion-gold-fill"), c("medallion-gold-stroke"), c("medallion-gold-ink"), "GOLD"),
        "serving": (c("medallion-serving-fill"), c("medallion-serving-stroke"), c("medallion-serving-ink"), "SERVING"),
    }
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="t d"><title id="t">EDA Retail Lakehouse architecture</title>'
           f'<desc id="d">Source table flows through Bronze deduplication into Silver cleaned, stitched and quarantine tables, '
           f'then Gold daily KPIs and customer features, then Genie, MCP server and MLflow model. '
           f'Cross-cutting controls: Delta CHECK constraints, dual-engine parity, Unity Catalog masks and row filters.</desc>',
           f'<style>text{{font-family:{SANS}}} .m{{font-family:{MONO}}} '
           f'.lbl{{font-size:11px;font-weight:700;letter-spacing:2px}} .nm{{font-size:13px;font-weight:700;fill:{c("ink-primary")}}} '
           f'.sb{{font-size:12.5px;fill:{c("ink-muted")}}} .ctl{{font-size:12.5px;fill:{c("ink-body")}}}</style>',
           f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           f'<path d="M0 0L10 5L0 10z" fill="{c("ink-muted")}"/></marker></defs>',
           f'<rect width="{W}" height="{H}" rx="14" fill="{c("bg")}"/>']

    for key, x in COLS.items():
        fill, stroke, ink, label = panels[key]
        h = 234 if key == "gold" else 334
        out.append(f'<rect x="{x-10}" y="{PANEL_Y}" width="{PANEL_W}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        out.append(f'<text x="{x}" y="84" class="lbl" fill="{ink}">{label}</text>')

    def node(col, slot, name, sub, stroke_key=None):
        x, y = COLS[col], SLOT[slot]
        stroke = panels[stroke_key or col][1]
        out.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="6" fill="{c("surface")}" stroke="{stroke}" stroke-width="1.25"/>')
        out.append(f'<text x="{x+14}" y="{y+27}" class="nm m">{name}</text>')
        out.append(f'<text x="{x+14}" y="{y+47}" class="sb">{sub}</text>')

    def arrow(d):
        out.append(f'<path d="{d}" fill="none" stroke="{c("ink-muted")}" stroke-width="1.5" marker-end="url(#a)"/>')

    node("source", 1, "transactions_raw", "retail_source · 1.07M rows")
    node("bronze", 1, "transactions_raw", "dedup · 22,523 rows dropped")
    node("silver", 0, "sales_cleaned", "typed · sale + cancellation")
    node("silver", 1, "sales_stitched", "guest checkouts resolved")
    node("silver", 2, "sales_quarantine", "non-product lines · audit only")
    node("gold", 0, "gold_daily_kpis", "revenue · orders · AOV")
    node("gold", 1, "gold_customer_features", "RFM · LTV · return rate")
    node("serving", 0, "Genie agent", "plain English → SQL → charts")
    node("serving", 1, "MCP server", "6 business-shaped tools")
    node("serving", 2, "MLflow model", "return risk · ROC-AUC 0.89")

    arrow("M240 236 H300")                                  # source -> bronze
    arrow("M500 236 H530 V136 H560")                         # bronze -> cleaned
    out.append(f'<path d="M530 236 V336 H560" fill="none" stroke="{c("ink-muted")}" stroke-width="1.5" marker-end="url(#a)"/>')  # -> quarantine
    arrow("M660 168 V204")                                   # cleaned -> stitched
    arrow("M760 136 H820")                                   # cleaned -> daily kpis
    arrow("M760 236 H820")                                   # stitched -> customer features
    arrow("M1030 175 H1070")                                 # gold -> serving

    gov = c("accent-navy")
    out.append(f'<rect x="30" y="424" width="1260" height="64" rx="14" fill="none" stroke="{gov}" stroke-width="1.5" stroke-dasharray="6 5"/>')
    out.append(f'<text x="50" y="448" class="lbl" fill="{gov}">CROSS-CUTTING CONTROLS</text>')
    for x, t in ((50, "Delta CHECK constraints on Silver; bad rows quarantined"),
                 (480, "Dual-engine parity: PySpark = Spark SQL, diff 0.00"),
                 (860, "Unity Catalog: customer_id mask, UK row filter")):
        out.append(f'<circle cx="{x+4}" cy="468" r="3.5" fill="{c("accent-green")}"/><text x="{x+16}" y="472" class="ctl">{t}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for theme in ("light", "dark"):
        p = ROOT / f"assets/architecture-{theme}.svg"
        p.write_text(render(theme))
        print("wrote", p.relative_to(ROOT))
