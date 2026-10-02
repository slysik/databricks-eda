"""Build the analytical presentation HTML from an executed run of eda_online_retail_ii.py.

The notebook is the single source of truth: every word, table, KPI tile, chart,
and parity verification check in the presentation is taken directly from the
Databricks run export, ensuring zero drift between notebook execution and report.

Usage:
    uv run --with markdown python build_presentation.py eda_online_retail_ii_run_export.html eda_online_retail_ii_presentation.html
"""
import base64
import html
import json
import re
import sys
import urllib.parse

import markdown

NAVY, BLUE, ORANGE, GREEN = "#1e4fa3", "#2a78d6", "#d9541e", "#198754"


def load_model(export_path: str) -> dict:
    """Decode the notebook model Databricks embeds in its HTML export."""
    raw = open(export_path, encoding="utf-8").read()
    blob = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", raw).group(1)
    return json.loads(urllib.parse.unquote(base64.b64decode(blob).decode()))


LIST_ITEM = re.compile(r"^\s*([*\-]|\d+\.)\s")


def md(text: str) -> str:
    """Databricks markdown -> HTML. Databricks nests lists with 2 spaces and allows a list
    straight after a paragraph; Python-Markdown needs 4 spaces and a blank line."""
    lines, out = text.split("\n"), []
    for line in lines:
        if LIST_ITEM.match(line):
            indent = len(line) - len(line.lstrip())
            line = " " * (indent * 2) + line.lstrip()
            if out and out[-1].strip() and not LIST_ITEM.match(out[-1]) and not out[-1].startswith(" "):
                out.append("")
        out.append(line)
    return markdown.markdown("\n".join(out), extensions=["tables", "sane_lists"])


ID_COLUMNS = {"stock_code", "invoice", "customer_id", "composite_key"}


def fmt(v, col: str = "") -> str:
    """Format table cell values with appropriate type formatting."""
    if col in ID_COLUMNS:
        return html.escape(str(v)) if v is not None else "–"
    if v is None:
        return "–"
    if isinstance(v, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00\.000Z", v):
            return v[:10]
        try:
            fv = float(v)
            if "pct" in col or "rate" in col:
                return f"{fv:.1f}%"
            if "revenue" in col or "amount" in col or "price" in col or "total" in col or "impact" in col:
                return f"{fv:,.2f}"
            if fv.is_integer() and abs(fv) >= 1000:
                return f"{int(fv):,}"
        except ValueError:
            pass
        return html.escape(v)
    if isinstance(v, float):
        if "pct" in col or "rate" in col:
            return f"{v:.1f}%"
        if "revenue" in col or "impact" in col or "amount" in col or "monetary" in col or "price" in col:
            return f"{v:,.2f}"
        if -1.0 <= v <= 1.0 and ("qty" in col or "price" in col or "total" in col or "flag" in col):
            return f"{v:+.3f}"
        if abs(v) >= 1000:
            return f"{v:,.2f}"
        return f"{v:.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return html.escape(str(v))


def kpi_tiles(rows: list) -> str:
    """Render executive KPI summary tiles."""
    tiles = []
    for item in rows:
        if len(item) >= 2:
            val, lbl = item[0], item[1]
            if any(str(val).startswith(p) for p in ["Gross", "Net", "Refund", "Active", "Guest", "International", "Total"]):
                val, lbl = item[1], item[0]
            color = ORANGE if any(w in str(lbl).lower() for w in ["refund", "loss", "risk", "lost"]) or str(val).startswith(("-", "−")) else (BLUE if str(val).startswith("+") else NAVY)
            shown = str(val).replace("-", "−")
            tiles.append(f'<div class="kpi"><div class="v" style="color:{color}">{html.escape(shown)}</div>'
                         f'<div class="l">{html.escape(str(lbl))}</div></div>')
    return f'<div class="kpis">{"".join(tiles)}</div>'


def table(schema: list, rows: list) -> str:
    """Render structured data table."""
    head = "".join(f"<th>{html.escape(c['name'].replace('_', ' '))}</th>" for c in schema)
    names = [c["name"] for c in schema]
    body = "".join("<tr>" + "".join(f"<td>{fmt(v, n)}</td>" for v, n in zip(r, names)) + "</tr>" for r in rows[:15])
    return f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def ansi_block(text: str) -> str:
    """Parse and render ANSI terminal outputs, parity tests, and execution logs."""
    text = text.strip()
    if not text:
        return ""
    if text == "[PASS: PySpark == SQL] Results match exactly.":
        return ('<div class="badge-parity"><span class="badge-icon">✓</span> '
                '<span class="badge-title"><strong>Dual-Engine Parity Verified:</strong> '
                'PySpark == SQL results match exactly within tolerance</span></div>')
    if text.startswith("Deduplicated:") and "[PASS: PySpark == SQL]" in text:
        parts = text.split("\n\n")
        out = []
        for p in parts:
            if "PASS: PySpark == SQL" in p:
                out.append('<div class="badge-parity"><span class="badge-icon">✓</span> '
                           '<span class="badge-title"><strong>Dual-Engine Parity Verified:</strong> '
                           'PySpark == SQL results match exactly within tolerance</span></div>')
            else:
                out.append(f'<div class="callout-note">{html.escape(p)}</div>')
        return "".join(out)
    if text.startswith(("Top 5 months", "Correlation matrix")):
        return f'<div class="tbl-heading"><strong>{html.escape(text)}</strong></div>'
    if "WARNING mlflow" in text:
        return (f'<details class="ml-log"><summary>MLflow Experiment Tracking & Logging</summary>'
                f'<pre><code>{html.escape(text)}</code></pre></details>')
    return f'<div class="term-box"><pre><code>{html.escape(text)}</code></pre></div>'


def code_block(cmd: str) -> str:
    """Render collapsable source code blocks."""
    lang = "SQL" if cmd.lstrip().startswith("%sql") else "Python"
    code = re.sub(r"^%(sql|python)\s*\n", "", cmd.lstrip())
    return (f'<details class="code"><summary>Show {lang}</summary>'
            f"<pre><code>{html.escape(code.strip())}</code></pre></details>")


def build(model: dict) -> str:
    parts, title_html, setup = [], "", None
    for cmd in model["commands"]:
        text = cmd["command"]
        if text.lstrip().startswith("%pip"):
            continue

        # Detect blueprint title card whether defined as %md or displayHTML
        if not title_html and ("Online Retail II - EDA" in text or text.lstrip().startswith("# Online") or "<h1" in text):
            h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.DOTALL)
            md_match = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            title_text = h1_match.group(1).strip() if h1_match else (md_match.group(1).strip() if md_match else "Online Retail II - EDA & Production Blueprint")
            
            clean_body = re.sub(r"</?div[^>]*>", "", text)
            clean_body = re.sub(r"<h1[^>]*>.*?</h1>", "", clean_body, flags=re.DOTALL)
            clean_body = re.sub(r"^#\s+.+?$", "", clean_body, flags=re.MULTILINE)
            clean_body = re.sub(r'displayHTML\("""|"""\)', "", clean_body)
            clean_body = re.sub(r"^%md\s*", "", clean_body).strip()
            
            title_html = (f'<header class="hero"><div class="kicker">Databricks Technical Blueprint & EDA</div>'
                          f"<h1>{html.escape(title_text)}</h1><div class='sub'>{md(clean_body)}</div></header>")
            continue

        if text.lstrip().startswith("%md"):
            body = re.sub(r"^%md\s*\n", "", text.lstrip())
            if setup is not None:
                parts.append(f'<details class="setup"><summary>{setup[0]}</summary>{"".join(setup[1])}</details>')
                setup = None
            if body.startswith("**Setup"):
                setup = (re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body.strip()), [])
                continue
            parts.append(f'<section class="md">{md(body)}</section>')
            continue

        out = []
        for r in (cmd.get("results") or {}).get("data") or []:
            if not isinstance(r, dict):
                continue
            if r.get("type") == "table":
                cols = [c["name"] for c in r.get("schema", [])]
                if cols == ["kpi", "label"]:
                    out.append(kpi_tiles(r["data"]))
                elif cols == ["Metric", "Value"] and any("Sales" in row[0] for row in r["data"]):
                    out.append(kpi_tiles(r["data"]))
                else:
                    out.append(table(r["schema"], r["data"]))
            elif r.get("type") == "mimeBundle" and "image/png" in r.get("data", {}):
                out.append(f'<figure><img alt="chart" src="data:image/png;base64,{r["data"]["image/png"]}"></figure>')
            elif r.get("type") == "ansi":
                b = ansi_block(r.get("data", ""))
                if b:
                    out.append(b)

        cell = f'<div class="cell">{"".join(out)}{code_block(text)}</div>'
        (setup[1] if setup is not None else parts).append(cell)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Online Retail II - EDA & Production Blueprint</title>
<style>
:root{{--navy:{NAVY};--ink:#141414;--mut:#5c5c5c;--line:#e6e5e1;--panel:#f4f7fc;--bg:#fff}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--ink:#ececec;--mut:#b4b4b4;--line:#33363d;--panel:#1b2230;--bg:#111317}}}}
:root[data-theme="dark"]{{--ink:#ececec;--mut:#b4b4b4;--line:#33363d;--panel:#1b2230;--bg:#111317}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);
line-height:1.6;max-width:1040px;margin:0 auto;padding:0 20px 64px}}
.hero{{background:linear-gradient(135deg,#12315f,#1e4fa3);color:#fff;margin:0 -20px 16px;padding:44px 32px 36px;border-radius:0 0 16px 16px}}
.hero .kicker{{font-size:12px;letter-spacing:2.5px;text-transform:uppercase;color:#bcd2f2}}
.hero h1{{font-size:clamp(24px,4vw,34px);line-height:1.2;margin:8px 0 10px}}
.hero .sub, .hero .sub p{{color:#d7e4f8;font-size:14.5px;margin:6px 0}}
.hero code{{background:rgba(255,255,255,.15);color:#fff}}
h2{{color:var(--navy);font-size:22px;margin:42px 0 10px;padding-top:14px;border-top:2px solid var(--line)}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]) h2,:root:not([data-theme="light"]) h3{{color:#8fb4ee}}}}
h3{{color:var(--navy);font-size:17px;margin:24px 0 6px}}
p,li{{font-size:15px}} ul,ol{{padding-left:22px}}
code{{background:var(--panel);padding:1px 5px;border-radius:4px;font-size:13px}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0 12px}}
@media (max-width:700px){{.kpis{{grid-template-columns:1fr}}}}
.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px}}
.kpi .v{{font-size:26px;font-weight:700}} .kpi .l{{font-size:13px;color:var(--mut);margin-top:2px}}
.tbl{{overflow-x:auto;margin:12px 0}}
table{{border-collapse:collapse;font-size:13.5px;width:100%}}
th{{text-align:left;color:var(--mut);font-weight:600;border-bottom:2px solid var(--line);padding:7px 10px;white-space:nowrap}}
td{{border-bottom:1px solid var(--line);padding:7px 10px;vertical-align:top}}
.md table td,.md table th{{font-size:14px}}
figure{{margin:18px 0}} figure img{{max-width:100%;height:auto;border-radius:8px;background:#fff;border:1px solid var(--line)}}
.badge-parity{{background:#eef7ee;border:1px solid #7bc67b;color:#186118;padding:8px 14px;border-radius:8px;font-size:13.5px;margin:8px 0 12px;display:flex;align-items:center;gap:8px}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]) .badge-parity{{background:#17291a;border-color:#2a6a32;color:#7ad887}}}}
.badge-parity .badge-icon{{color:{GREEN};font-weight:bold;font-size:16px}}
.callout-note{{background:var(--panel);border-left:4px solid var(--navy);padding:8px 14px;border-radius:4px;margin:8px 0 10px;font-size:13.5px}}
.tbl-heading{{font-size:13.5px;font-weight:600;color:var(--mut);margin:14px 0 4px}}
.term-box pre{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;font-size:12.5px;line-height:1.45;overflow-x:auto;margin:8px 0 12px}}
details.ml-log{{margin:6px 0 12px}} details.ml-log summary{{cursor:pointer;color:var(--mut);font-size:12.5px}}
details.ml-log pre{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;font-size:12px}}
details.setup{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:16px 0;font-size:14px}}
details.setup summary{{cursor:pointer}}
details.code{{margin:4px 0 14px}} details.code summary{{cursor:pointer;color:var(--mut);font-size:12.5px}}
details.code pre{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;overflow-x:auto;font-size:12px;line-height:1.45}}
hr{{border:none;border-top:1px solid var(--line);margin:30px 0}}
footer{{color:var(--mut);font-size:12.5px;margin-top:40px;border-top:1px solid var(--line);padding-top:16px}}
</style></head><body>
{title_html}
{"".join(parts)}
<footer>Generated from an executed run of <code>eda_online_retail_ii.py</code> on Databricks: every number, table, parity check, and chart above is that run's verified output.</footer>
</body></html>"""


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "w", encoding="utf-8").write(build(load_model(src)))
    print(f"wrote {dst}")
