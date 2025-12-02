import json
import io
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import pandas as pd

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
ATT_DIR.mkdir(exist_ok=True)

DEFAULT_FILE = DATA_DIR / "default_flow.json"


# ------------------------------------------------------
# STYLE / CONSTANTS
# ------------------------------------------------------
PAGE_CSS = """
<style>
.stApp {
    background-color: #f5f5f7;
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

/* Phase chevrons */
.phase-row {
    display: flex;
    gap: 8px;
    margin: 10px 0 25px 0;
    justify-content: center;
}
.phase-chevron {
    position: relative;
    padding: 14px 28px;
    background: #ffe58a;
    color: #333;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-size: 13px;
    clip-path: polygon(0 0, 90% 0, 100% 50%, 90% 100%, 0 100%, 10% 50%);
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

/* Step cards under the flow */
.step-flow-container {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 10px 4px 0 4px;
    gap: 10px;
}
.step-card {
    min-width: 130px;
    max-width: 150px;
    background: white;
    border-radius: 8px;
    padding: 8px 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    font-size: 11px;
    position: relative;
    border-top: 3px solid #ddd;
    cursor: default;
}
.step-card-title {
    font-weight: 600;
    margin-bottom: 4px;
}
.step-card-meta {
    color: #666;
    font-size: 10px;
}
.step-card-path-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    display: inline-block;
    margin-right: 4px;
}

/* Legend */
.legend-box {
    margin-top: 12px;
    background: white;
    border-radius: 10px;
    padding: 8px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    font-size: 11px;
}
.legend-item {
    display: inline-flex;
    align-items: center;
    margin-right: 14px;
}
.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    margin-right: 5px;
}

/* For narrower screens */
@media (max-width: 900px) {
    .phase-row {
        flex-direction: column;
        align-items: stretch;
    }
}
</style>
"""

PHASES = [
    "Pilot & Initiate",
    "Prepare & Startup",
    "Execute & Adopt",
    "Close & Sustain",
]

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
# FLOW VISUAL (PHASES + MINI CARDS)
# ------------------------------------------------------
def render_phase_row():
    html = '<div class="phase-row">'
    for phase in PHASES:
        html += f'<div class="phase-chevron">{phase}</div>'
    html += "</div>"
    return html


def render_step_flow(data: Dict[str, Any]) -> str:
    nodes = data.get("nodes", [])

    html = '<div class="step-flow-container">'
    for node in nodes:
        label = node.get("label", "")
        phase = node.get("phase", "")
        status = node.get("status", "")
        time_est = node.get("time_estimate", "")
        success = node.get("success_rate", "")
        volume = node.get("volume_pct", "")
        owner = node.get("owner", "")

        path = node.get("path") or DEFAULT_PATH
        color = PATH_COLORS.get(path, "#9ca3af")

        tooltip_lines = [
            f"Phase: {phase}",
            f"Path: {path}",
            f"Status: {status or 'N/A'}",
            f"Owner: {owner or 'N/A'}",
            f"Time: {time_est or 'N/A'}",
            f"Success: {success or 'N/A'}",
            f"Volume: {volume or 'N/A'}%",
        ]
        tooltip = "&#10;".join(tooltip_lines)  # newline in HTML title attribute

        meta_parts = []
        if status:
            meta_parts.append(status)
        if time_est:
            meta_parts.append(time_est)
        if success:
            meta_parts.append(f"{success} success")

        html += f"""
        <div class="step-card" title="{tooltip}">
          <div class="step-card-title">
            <span class="step-card-path-dot" style="background:{color};"></span>{label}
          </div>
          <div class="step-card-meta">{phase}</div>
          <div class="step-card-meta">{' · '.join(meta_parts)}</div>
        </div>
        """

    html += "</div>"
    return html


def render_legend(data: Dict[str, Any]) -> str:
    # Calculate simple distribution by path
    counts = {p: 0 for p in PATH_COLORS.keys()}
    for node in data.get("nodes", []):
        path = node.get("path") or DEFAULT_PATH
        if path in counts:
            counts[path] += 1

    total = sum(counts.values()) or 1

    html = '<div class="legend-box"><strong>Paths</strong> &nbsp;'
    for path, color in PATH_COLORS.items():
        pct = round(100 * counts[path] / total, 1) if total else 0
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
    st.caption("Report-style overview of your launch journey with branching paths, mini cards, and PDF export.")

    # Sidebar – File handling
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
    left, right = st.columns([2.2, 1.8])

    with left:
        st.subheader("Flow Overview")
        st.markdown(render_phase_row(), unsafe_allow_html=True)
        st.markdown(render_step_flow(data), unsafe_allow_html=True)
        st.markdown(render_legend(data), unsafe_allow_html=True)

        st.markdown("### Export as PDF")
        if not REPORTLAB_AVAILABLE:
            st.warning("PDF export requires the 'reportlab' package. Add it to requirements.txt.")
        else:
            mode = st.selectbox("Report type", ["Summary (1 page)", "Detailed (multi-page)"])
            mode_key = "summary" if mode.startswith("Summary") else "detailed"
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
