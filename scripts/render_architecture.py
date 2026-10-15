#!/usr/bin/env python3
"""Render assets/architecture-{light,dark}.svg from design/tokens.json.

Usage: python3 scripts/render_architecture.py        (stdlib only)

Colours come from the token file, so a palette change is one edit plus one run.
Layout: source card, one Lakeflow card holding the Bronze/Silver/Gold cylinders, a Lakehouse card, three serving cards, and a governance panel across the top.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOK = {t["name"]: t["value"] for t in json.loads((ROOT / "design/tokens.json").read_text())["color"]["tokens"]}
SANS = json.loads((ROOT / "design/tokens.json").read_text())["type"]["families"]["sans"].replace('"', "'")
MONO = json.loads((ROOT / "design/tokens.json").read_text())["type"]["families"]["mono"].replace('"', "'")

W, H = 1320, 460
MID = 300  # centre line of the main flow


def inline_text(svg: str, theme: str) -> str:
    """Turn class/style on <text> into presentation attributes (no <style> block: some hosts strip it)."""
    c = lambda n: TOK[n][theme]
    base = {"font-family": SANS}
    cls = {"m": {"font-family": MONO},
           "h": {"font-size": "14", "font-weight": "700", "fill": c("ink-primary")},
           "nm": {"font-size": "13", "font-weight": "700", "fill": c("ink-primary")},
           "sb": {"font-size": "12", "fill": c("ink-muted")},
           "xs": {"font-size": "11", "fill": c("ink-muted")},
           "lb": {"font-size": "11", "font-weight": "700", "letter-spacing": "1.5"}}

    def fix(m):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        out = dict(base)
        for k in attrs.pop("class", "").split():
            out.update(cls[k])
        for decl in attrs.pop("style", "").split(";"):
            if decl.strip():
                k, v = decl.split(":")
                out[k.strip()] = v.strip().replace("px", "")
        out.update(attrs)
        return "<text " + " ".join(f'{k}="{v.replace(chr(34), chr(39))}"' for k, v in out.items()) + ">"
    return re.sub(r"<text ([^>]*)>", fix, svg)


def render(theme: str) -> str:
    c = lambda n: TOK[n][theme]
    ink, mute, line, surf, bg = c("ink-primary"), c("ink-muted"), c("line-strong") if theme == "dark" else c("line"), c("surface"), c("bg")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
           f'<title id="t">EDA Retail Lakehouse architecture</title>'
           f'<desc id="d">A Unity Catalog source table flows into Lakeflow, where Bronze, Silver and Gold layers are built, then into governed Gold tables. '
           f'Genie and an MCP server read the Gold tables; a dashed MLflow model card is trained in a notebook and not served. A governance panel above lists Unity Catalog access controls, Delta quality checks and, dashed, dual-engine parity that lives in a notebook.</desc>',
           f'<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="{0.10 if theme == "light" else 0.40}"/></filter>'
           f'<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{mute}"/></marker></defs>',
           f'<rect width="{W}" height="{H}" rx="14" fill="{bg}"/>']

    def card(x, y, w, h, rx=12, fill=None, shadow=True, dashed=False):
        f = ' filter="url(#sh)"' if shadow else ""
        d = f' stroke-dasharray="5 4"' if dashed else ""
        st = mute if dashed else line
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or surf}" stroke="{st}" stroke-width="1"{d}{f}/>')

    def link(d, dot=None, dashed=False):
        da = ' stroke-dasharray="4 3"' if dashed else ""
        out.append(f'<path d="{d}" fill="none" stroke="{mute}" stroke-width="1.25"{da} marker-end="url(#a)"/>')
        if dot:
            out.append(f'<circle cx="{dot[0]}" cy="{dot[1]}" r="3.5" fill="{c("brand-orange")}"/>')

    # title
    out.append(f'<text x="40" y="52" class="h" style="font-size:16px">EDA Retail Lakehouse</text>')
    out.append(f'<text x="40" y="72" class="sb">Online Retail II · Dec 2009 to Dec 2011</text>')

    # governance panel (top right)
    card(640, 20, 640, 104, rx=14)
    out.append(f'<text x="656" y="44" class="nm" style="fill:{c("accent-navy")}">Governance and quality</text>')
    for i, (t, sub) in enumerate((("Unity Catalog access", "customer_id mask · UK row filter"),
                                  ("Delta quality", "CHECK constraints · quarantine"),
                                  ("Dual-engine parity", "PySpark = SQL, notebook only"))):
        x = 654 + i * 208
        card(x, 56, 196, 54, rx=8, fill=c("surface-alt"), shadow=False, dashed=(i == 2))
        out.append(f'<circle cx="{x+14}" cy="76" r="3.5" fill="{c("accent-green") if i < 2 else c("ink-faint")}"/>')
        out.append(f'<text x="{x+26}" y="80" class="nm">{t}</text>')
        out.append(f'<text x="{x+12}" y="98" class="xs">{sub}</text>')

    # source card
    card(40, MID - 42, 200, 84)
    out.append(f'<text x="56" y="{MID-18}" class="lb" style="fill:{c("accent-blue")}">UNITY CATALOG TABLE</text>')
    out.append(f'<text x="56" y="{MID+6}" class="nm m">transactions_raw</text>')
    out.append(f'<text x="56" y="{MID+26}" class="sb">retail_source · 1.07M rows</text>')

    # Lakeflow card with medallion cylinders
    card(300, 185, 340, 230, rx=16)
    out.append(f'<text x="320" y="214" class="h">Lakeflow</text><text x="388" y="214" class="sb">ingest, clean, aggregate</text>')
    out.append(f'<rect x="316" y="228" width="308" height="124" rx="10" fill="{c("surface-alt")}"/>')
    for cx, k, label, sub in ((370, "bronze", "BRONZE", "dedup"), (470, "silver", "SILVER", "clean · quarantine"), (570, "gold", "GOLD", "KPIs · RFM")):
        f, st, ik = c(f"medallion-{k}-fill"), c(f"medallion-{k}-stroke"), c(f"medallion-{k}-ink")
        out.append(f'<path d="M{cx-28} 252v38a28 8 0 0 0 56 0v-38" fill="{f}" stroke="{st}" stroke-width="1.5"/>')
        out.append(f'<ellipse cx="{cx}" cy="252" rx="28" ry="8" fill="{f}" stroke="{st}" stroke-width="1.5"/>')
        out.append(f'<text x="{cx}" y="320" class="lb" text-anchor="middle" style="fill:{ik}">{label}</text>')
        out.append(f'<text x="{cx}" y="338" class="xs" text-anchor="middle">{sub}</text>')
    for x in (402, 502):
        out.append(f'<line x1="{x}" y1="274" x2="{x+36}" y2="274" stroke="{mute}" stroke-width="1.25" stroke-dasharray="3 3"/>')
    out.append(f'<text x="320" y="384" class="xs">Notebooks or declarative pipelines (ADR-005)</text>')
    out.append(f'<text x="320" y="402" class="xs">CHECK constraints and quarantine run in Silver</text>')

    # lakehouse card
    card(700, MID - 36, 220, 72)
    out.append(f'<text x="716" y="{MID-8}" class="nm">Gold tables</text>')
    out.append(f'<text x="716" y="{MID+14}" class="sb">daily KPIs · customer features</text>')

    # serving cards
    for i, (n, sub) in enumerate((("Genie agent", "LLM writes SQL over Gold tables"),
                                  ("MCP server", "6 tools · rule-based risk score"),
                                  ("MLflow model", "notebook only · not served"))):
        y = 178 + i * 90
        card(1000, y, 280, 64, dashed=(i == 2))
        out.append(f'<text x="1018" y="{y+27}" class="nm">{n}</text><text x="1018" y="{y+47}" class="sb">{sub}</text>')

    # connectors, each starting with a brand-orange dot
    link(f"M240 {MID} H300", (240, MID))
    link(f"M640 {MID} H700", (640, MID))
    for i in range(3):
        link(f"M920 {MID} H960 V{210+i*90} H1000" if i != 1 else f"M920 {MID} H1000", (920, MID) if i == 0 else None, dashed=(i == 2))
    out.append("</svg>")
    return inline_text("\n".join(out) + "\n", theme)


if __name__ == "__main__":
    for theme in ("light", "dark"):
        p = ROOT / f"assets/architecture-{theme}.svg"
        p.write_text(render(theme))
        print("wrote", p.relative_to(ROOT))
