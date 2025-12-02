import json
import io
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ------------------------------------------------------
# PATHS
# ------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ATT_DIR = DATA_DIR / "attachments"

DATA_DIR.mkdir(exist_ok=True)
ATT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_FILE = DATA_DIR / "default_flow.json"


# ------------------------------------------------------
# STYLE / CONSTANTS
# ------------------------------------------------------
PAGE_CSS = """
<style>
.stApp {
    background-color: #f4f4f7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Top metrics */
.big-metric {
    font-size: 30px;
    font-weight: 700;
}
.big-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #666;
    margin-top: -6px;
}

/* Legend */
.legend-box {
    margin-top: 10px;
    background: #ffffff;
    border-radius: 10px;
    padding: 8px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    font-size: 11px;
}
.legend-item {
    display: inline-flex;
    align-items: center;
    margin-right: 16px;
}
.legend-dot {
    width: 11px;
    height: 11px;
    border-radius: 999px;
    margin-right: 6px;
}
</style>
"""

PHASES = [
    "Pilot & Initiate",
    "Prepare & Startup",
    "Execute & Adopt",
    "Close & Sustain",
]

PHASE_COLORS = {
    "Pilot & Initiate": "#ffe7b8",
    "Prepare & Startup": "#e8f4d9",
    "Execute & Adopt": "#e7e8fb",
    "Close & Sustain": "#f8f1c7",
}

PATH_COLORS = {
    "Primary": "#16a34a",   # green
    "Data Prep": "#f97316", # orange
    "Enhanced": "#6366f1",  # indigo
    "Exit": "#ef4444",      # red
}

DEFAULT_PATH = "Primary"


# ------------------------------------------------------
# FILE OPERATIONS
# ------------------------------------------------------
def load_launch(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_launch(data: Dict[str, Any], path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_launch_files() -> List[Path]:
    return sorted([p for p in DATA_DIR.glob("*.json")])


# ------------------------------------------------------
# METRICS
# ------------------------------------------------------
def compute_metrics(data: Dict[str, Any]):
    nodes = data.get("nodes", [])
    total_steps = len(nodes)
    active_steps = sum(1 for n in nodes if n.get("status") in ["In progress", "Planned"])

    success_vals = []
    for n in nodes:
        raw = str(n.get("success_rate", "")).replace("%", "").strip()
        try:
            success_vals.append(float(raw))
        except Exception:
            pass
    avg_success = round(sum(success_vals) / len(success_vals), 1) if success_vals else None
    return total_steps, active_steps, avg_success


def render_metrics(data: Dict[str, Any]):
    total_steps, active_steps, avg_success = compute_metrics(data)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<p class='big-metric'>{total_steps}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Steps</p>", unsafe_allow_html=True)
    with c2:
        txt = f"{avg_success}%" if avg_success is not None else "—"
        st.markdown(f"<p class='big-metric'>{txt}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Avg Success</p>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<p class='big-metric'>{active_steps}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Active</p>", unsafe_allow_html=True)


# ------------------------------------------------------
# ENTERPRISE FLOW MAP (SVG)
# ------------------------------------------------------
def _truncate(text: str, max_len: int) -> str:
    text = text or ""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def build_flow_svg(data: Dict[str, Any]) -> str:
    """
    Returns full HTML (svg inside a div) to embed via components.html
    """
    nodes = data.get("nodes", [])
    if not nodes:
        return "<div>No steps defined.</div>"

    width = 1300
    height = 420

    n = len(nodes)
    margin_x = 100
    usable_width = width - 2 * margin_x
    if n > 1:
        step_x = usable_width / (n - 1)
    else:
        step_x = 0

    center_y = 220
    card_w = 190
    card_h = 110
    ribbon_y_offset = 60

    # Precompute positions
    positions = []
    for i in range(n):
        x = margin_x + i * step_x
        positions.append((x, center_y))

    # Start SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<filter id="cardShadow" x="-20%" y="-20%" width="140%" height="140%">'
        '  <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.12)"/>'
        '</filter>'
        '</defs>'
        # background
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f6f8" />'
    ]

    # Ribbons (behind cards)
    for i in range(n - 1):
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]
        node = nodes[i]
        path = node.get("path") or DEFAULT_PATH
        color = PATH_COLORS.get(path, "#d4d4d8")

        ctrl1_x = x1 + step_x * 0.35
        ctrl2_x = x2 - step_x * 0.35
        ctrl_y = center_y - ribbon_y_offset

        path_d = (
            f"M{x1},{y1} "
            f"C{ctrl1_x},{ctrl_y} {ctrl2_x},{ctrl_y} {x2},{y2}"
        )

        svg_parts.append(
            f'<path d="{path_d}" stroke="{color}" stroke-opacity="0.45" '
            f'stroke-width="14" fill="none" />'
        )

    # Phase chevrons behind (simple rectangles w/ notches effect)
    phase_band_y = 70
    phase_band_h = 40
    phase_width = usable_width / len(PHASES)
    for idx, phase in enumerate(PHASES):
        x0 = margin_x + idx * phase_width
        x1 = x0 + phase_width
        fill = PHASE_COLORS.get(phase, "#ffe7b8")
        svg_parts.append(
            f'<rect x="{x0}" y="{phase_band_y}" width="{phase_width-10}" '
            f'height="{phase_band_h}" rx="4" ry="4" fill="{fill}" />'
        )
        svg_parts.append(
            f'<text x="{x0 + (phase_width-10)/2}" y="{phase_band_y + 25}" '
            f'font-size="13" font-weight="600" text-anchor="middle" '
            f'fill="#333">{phase.upper()}</text>'
        )

    # Cards
    for i, node in enumerate(nodes):
        x, y = positions[i]
        card_x = x - card_w / 2
        card_y = y - card_h / 2

        phase = node.get("phase", "")
        phase_fill = PHASE_COLORS.get(phase, "#fff7d6")

        label = _truncate(node.get("label", ""), 30)
        time_est = node.get("time_estimate", "")
        success = node.get("success_rate", "")
        volume = node.get("volume_pct", "")
        status = node.get("status", "")
        path = node.get("path") or DEFAULT_PATH
        path_color = PATH_COLORS.get(path, "#9ca3af")

        tooltip_lines = [
            f"Phase: {phase}",
            f"Path: {path}",
            f"Status: {status or 'N/A'}",
            f"Time: {time_est or 'N/A'}",
            f"Success: {success or 'N/A'}",
            f"Volume: {volume or 'N/A'}%",
        ]
        tooltip = "\\n".join(tooltip_lines)

        svg_parts.append('<g filter="url(#cardShadow)">')
        # Card base
        svg_parts.append(
            f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" '
            f'rx="10" ry="10" fill="#ffffff" stroke="#e5e7eb" />'
        )
        # Phase bar on top of card
        svg_parts.append(
            f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="22" '
            f'rx="10" ry="10" fill="{phase_fill}" />'
        )
        # Path dot
        svg_parts.append(
            f'<circle cx="{card_x + 14}" cy="{card_y + 11}" r="4" fill="{path_color}" />'
        )
        # Phase text
        svg_parts.append(
            f'<text x="{card_x + 26}" y="{card_y + 15}" font-size="10" '
            f'fill="#374151">{phase}</text>'
        )
        # Title
        svg_parts.append(
            f'<text x="{card_x + 14}" y="{card_y + 40}" font-size="12" '
            f'font-weight="600" fill="#111827">{label}</text>'
        )
        # Metrics line
        metrics = []
        if time_est:
            metrics.append(time_est)
        if success:
            metrics.append(f"{success} success")
        if volume not in ("", None):
            metrics.append(f"{volume}% volume")
        metrics_text = " · ".join(metrics)
        svg_parts.append(
            f'<text x="{card_x + 14}" y="{card_y + 64}" font-size="10" '
            f'fill="#6b7280">{metrics_text}</text>'
        )
        # Status
        if status:
            svg_parts.append(
                f'<text x="{card_x + 14}" y="{card_y + 86}" font-size="10" '
                f'fill="#4b5563">Status: {status}</text>'
            )

        # Tooltip
        svg_parts.append(f'<title>{tooltip}</title>')
        svg_parts.append('</g>')

    svg_parts.append("</svg>")

    svg = "".join(svg_parts)
    html = f"""
    <div style="width:100%; overflow-x:auto; padding:4px 0;">
      {svg}
    </div>
    """
    return html


def render_legend(data: Dict[str, Any]) -> str:
    counts = {p: 0 for p in PATH_COLORS.keys()}
    for node in data.get("nodes", []):
        path = node.get("path") or DEFAULT_PATH
        if path in counts:
            counts[path] += 1
    total = sum(counts.values()) or 1

    html = '<div class="legend-box"><strong>Paths</strong>&nbsp;'
    for path, color in PATH_COLORS.items():
        pct = round(100 * counts[path] / total, 1)
        html += f"""
        <span class="legend-item">
          <span class="legend-dot" style="background:{color};"></span>
          {path} ({counts[path]} · {pct}%)
        </span>
        """
    html += "</div>"
    return html


# ------------------------------------------------------
# STEP EDITOR
# ------------------------------------------------------
def render_node_editor(data: Dict[str, Any]):
    nodes = data.get("nodes", [])

    st.subheader("Step Details Editor")

    if not nodes:
        st.info("No steps in this launch file.")
        return

    labels = [f"{n['id']}. {n['label']}" for n in nodes]
    idx = st.selectbox("Select step", range(len(nodes)), format_func=lambda i: labels[i])
    node = nodes[idx]

    st.markdown("### Basic Info")
    node["label"] = st.text_input("Title", node.get("label", ""))

    node["phase"] = st.selectbox(
        "Phase",
        PHASES,
        index=PHASES.index(node.get("phase", PHASES[0])) if node.get("phase", PHASES[0]) in PHASES else 0,
    )

    node["path"] = st.selectbox(
        "Path (branch)",
        list(PATH_COLORS.keys()),
        index=list(PATH_COLORS.keys()).index(node.get("path", DEFAULT_PATH))
        if node.get("path", DEFAULT_PATH) in PATH_COLORS
        else 0,
    )

    node["description"] = st.text_area("Description", node.get("description", ""), height=80)

    st.markdown("### Metrics")
    c1, c2, c3 = st.columns(3)
    with c1:
        node["time_estimate"] = st.text_input("Time Estimate", node.get("time_estimate", ""))
    with c2:
        node["volume_pct"] = st.number_input(
            "Volume %",
            value=float(node.get("volume_pct", 100) or 100),
            min_value=0.0,
            max_value=100.0,
            step=1.0,
        )
    with c3:
        node["success_rate"] = st.text_input("Success Rate (%)", str(node.get("success_rate", "")))

    st.markdown("### Ownership & Notes")
    node["owner"] = st.text_input("Owner", node.get("owner", ""))
    node["status"] = st.selectbox(
        "Status",
        ["Planned", "In progress", "Blocked", "Completed"],
        index=["Planned", "In progress", "Blocked", "Completed"].index(node.get("status", "Planned")),
    )
    node["notes"] = st.text_area("Notes", node.get("notes", ""), height=80)

    st.markdown("### Links")
    links_text = "\n".join(node.get("links", []))
    updated_links = st.text_area("Links (one per line)", value=links_text)
    node["links"] = [l.strip() for l in updated_links.splitlines() if l.strip()]

    st.markdown("### Attachments")
    attachments = node.get("attachments", [])
    if attachments:
        st.caption("Existing files (paths):")
        for f in attachments:
            st.write("- " + f)

    uploaded = st.file_uploader("Upload files", accept_multiple_files=True)
    for f in uploaded:
        step_dir = ATT_DIR / f"step_{node['id']}"
        step_dir.mkdir(parents=True, exist_ok=True)
        file_path = step_dir / f.name
        with file_path.open("wb") as out:
            out.write(f.getbuffer())
        attachments.append(str(file_path.relative_to(BASE_DIR)))
    node["attachments"] = attachments


# ------------------------------------------------------
# PDF EXPORT
# ------------------------------------------------------
def build_pdf(data: Dict[str, Any], mode: str = "summary") -> bytes:
    """
    mode: 'summary' or 'detailed'
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    title = data.get("name", "Global Launch Navigator")
    total_steps, active_steps, avg_success = compute_metrics(data)

    # ---------- COVER / SUMMARY PAGE ----------
    y = height - 30 * mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(25 * mm, y, title)

    y -= 10 * mm
    c.setFont("Helvetica", 11)
    c.drawString(25 * mm, y, data.get("description", ""))

    # Metrics
    y -= 15 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, f"Steps: {total_steps}")
    c.drawString(70 * mm, y, f"Active: {active_steps}")
    avg_txt = f"{avg_success}%" if avg_success is not None else "—"
    c.drawString(120 * mm, y, f"Avg success: {avg_txt}")

    # Phase bar (simple rectangles)
    y -= 20 * mm
    phase_width = (width - 50 * mm) / len(PHASES)
    c.setFont("Helvetica-Bold", 9)
    for i, phase in enumerate(PHASES):
        x = 25 * mm + i * phase_width
        c.setFillColorRGB(1, 0.91, 0.6)  # soft yellow
        c.rect(x, y, phase_width - 4, 10 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(x + (phase_width - 4) / 2, y + 3.5 * mm, phase.upper())

    # Path legend
    y -= 15 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(25 * mm, y, "Paths:")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    x = 25 * mm
    counts = {p: 0 for p in PATH_COLORS}
    for node in data.get("nodes", []):
        path = node.get("path") or DEFAULT_PATH
        if path in counts:
            counts[path] += 1
    total = sum(counts.values()) or 1
    for path, color_hex in PATH_COLORS.items():
        r = int(color_hex[1:3], 16) / 255
        g = int(color_hex[3:5], 16) / 255
        b = int(color_hex[5:7], 16) / 255
        c.setFillColorRGB(r, g, b)
        c.rect(x, y, 4 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        pct = round(100 * counts[path] / total, 1)
        c.drawString(x + 6 * mm, y, f"{path} ({counts[path]} · {pct}%)")
        x += 40 * mm

    # Quick list of steps
    y -= 15 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, "Steps overview")
    y -= 8 * mm
    c.setFont("Helvetica", 9)

    for node in data.get("nodes", []):
        if y < 25 * mm:
            c.showPage()
            y = height - 25 * mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(25 * mm, y, "Steps overview (cont.)")
            y -= 8 * mm
            c.setFont("Helvetica", 9)

        path = node.get("path") or DEFAULT_PATH
        line = f"{node.get('id','')} – {node.get('label','')}  [{node.get('phase','')} · {path}]"
        c.drawString(25 * mm, y, line)
        y -= 5 * mm

    if mode == "detailed":
        # Detailed per-step pages
        for node in data.get("nodes", []):
            c.showPage()
            y = height - 30 * mm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(25 * mm, y, f"Step {node.get('id','')} – {node.get('label','')}")
            y -= 8 * mm
            c.setFont("Helvetica", 10)
            c.drawString(25 * mm, y, f"Phase: {node.get('phase','')}   Path: {node.get('path', DEFAULT_PATH)}")
            y -= 6 * mm
            c.drawString(
                25 * mm,
                y,
                f"Owner: {node.get('owner','N/A')}   Status: {node.get('status','N/A')}",
            )
            y -= 6 * mm
            c.drawString(
                25 * mm,
                y,
                f"Time: {node.get('time_estimate','N/A')}   Success: {node.get('success_rate','N/A')}   Volume: {node.get('volume_pct','N/A')}%",
            )
            y -= 10 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(25 * mm, y, "Description:")
            y -= 6 * mm
            c.setFont("Helvetica", 9)
            desc = node.get("description", "") or "—"
            for line in desc.splitlines():
                if y < 25 * mm:
                    c.showPage()
                    y = height - 25 * mm
                    c.setFont("Helvetica", 9)
                c.drawString(25 * mm, y, line)
                y -= 5 * mm

            y -= 8 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(25 * mm, y, "Notes:")
            y -= 6 * mm
            c.setFont("Helvetica", 9)
            notes = node.get("notes", "") or "—"
            for line in notes.splitlines():
                if y < 25 * mm:
                    c.showPage()
                    y = height - 25 * mm
                    c.setFont("Helvetica", 9)
                c.drawString(25 * mm, y, line)
                y -= 5 * mm

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ------------------------------------------------------
# MAIN APP
# ------------------------------------------------------
def main():
    st.set_page_config(page_title="Global Launch Navigator", layout="wide", page_icon="🧭")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    st.title("🧭 Global Launch Navigator")
    st.caption("Enterprise-style launch flow map with branching paths, mini cards, and PDF export.")

    # Sidebar – Launch files
    st.sidebar.header("Launch File")

    files = list_launch_files()
    if DEFAULT_FILE not in files:
        files.insert(0, DEFAULT_FILE)

    selected = st.sidebar.selectbox(
        "Select launch file",
        files,
        index=files.index(DEFAULT_FILE),
        format_func=lambda p: p.name,
    )

    if "launch" not in st.session_state or st.session_state["file"] != str(selected):
        st.session_state["launch"] = load_launch(selected)
        st.session_state["file"] = str(selected)

    data = st.session_state["launch"]

    save_name = st.sidebar.text_input("Save As (filename.json)", value=selected.name)
    if st.sidebar.button("Save"):
        save_launch(data, DATA_DIR / save_name)
        st.sidebar.success(f"Saved as {save_name}")

    # Metrics row
    render_metrics(data)
    st.markdown("---")

    # Layout
    left, right = st.columns([2.3, 1.7])

    with left:
        st.subheader("Flow Overview")
        svg_html = build_flow_svg(data)
        components.html(svg_html, height=440, scrolling=True)
        st.markdown(render_legend(data), unsafe_allow_html=True)

        st.markdown("### Export as PDF")
        if not REPORTLAB_AVAILABLE:
            st.warning("PDF export requires the 'reportlab' package. Add it to requirements.txt.")
        else:
            mode_label = st.selectbox("Report type", ["Summary (1 page)", "Detailed (multi-page)"])
            mode_key = "summary" if mode_label.startswith("Summary") else "detailed"
            pdf_bytes = build_pdf(data, mode=mode_key)
            st.download_button(
                "Download PDF report",
                data=pdf_bytes,
                file_name="launch_report.pdf",
                mime="application/pdf",
            )

    with right:
        render_node_editor(data)

    with st.expander("Show steps as table"):
        st.dataframe(pd.DataFrame(data.get("nodes", [])))


if __name__ == "__main__":
    main()
