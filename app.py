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
# PATHS & CONSTANTS
# ------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ATT_DIR = DATA_DIR / "attachments"

DATA_DIR.mkdir(exist_ok=True)
ATT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_FILE = DATA_DIR / "default_flow.json"

PHASES = [
    "Pilot & Initiate",
    "Prepare & Startup",
    "Execute & Adopt",
    "Close & Sustain",
]

PHASE_SHORT = {
    "Pilot & Initiate": "PILOT & INITIATE",
    "Prepare & Startup": "PREPARE & STARTUP",
    "Execute & Adopt": "EXECUTE & ADOPT",
    "Close & Sustain": "CLOSE & SUSTAIN",
}

# all phases same yellow – matches your slide
PHASE_COLOR_BAR = "#FFE7A3"

PATH_COLORS = {
    "Primary": "#16a34a",   # green
    "Data Prep": "#f97316", # orange
    "Enhanced": "#6366f1",  # indigo
    "Exit": "#ef4444",      # red
}
DEFAULT_PATH = "Primary"


# ------------------------------------------------------
# GLOBAL CSS (light, consulting style)
# ------------------------------------------------------
PAGE_CSS = """
<style>
.stApp {
    background-color: #f4f4f7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* top metrics */
.big-metric {
    font-size: 32px;
    font-weight: 700;
}
.big-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #666;
    margin-top: -6px;
}

/* phase chevron bar */
.chevron-row {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin: 4px 0 22px 0;
}
.chevron {
    padding: 14px 40px;
    background: #ffe7a3;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #262626;
    clip-path: polygon(0 0, 90% 0, 100% 50%, 90% 100%, 0 100%, 10% 50%);
    box-shadow: 0 1px 3px rgba(0,0,0,0.18);
}

/* overview grid */
.overview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 18px;
    margin-top: 6px;
}
.phase-column {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.phase-column-label {
    font-size: 11px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 2px;
}

/* step cards (overview) */
.step-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 10px 12px 8px 12px;
    box-shadow: 0 8px 18px rgba(15,23,42,0.06);
    border: 1px solid #e5e7eb;
    position: relative;
}
.step-card-header {
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin-bottom: 2px;
}
.step-badge {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #9ca3af;
}
.step-title {
    font-size: 12px;
    font-weight: 600;
    color: #111827;
}
.step-sub {
    font-size: 10px;
    color: #6b7280;
    margin-bottom: 2px;
}
.step-meta {
    font-size: 10px;
    color: #6b7280;
}
.path-pill {
    position: absolute;
    top: 8px;
    right: 10px;
    font-size: 9px;
    padding: 2px 8px;
    border-radius: 999px;
    color: white;
}

/* phase detail cards */
.phase-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 10px 22px rgba(15,23,42,0.08);
    border-left: 3px solid #e5e7eb;
    margin-bottom: 12px;
}
.phase-card-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}
.phase-card-title {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
}
.phase-card-phase {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #9ca3af;
}
.phase-card-meta {
    font-size: 11px;
    color: #6b7280;
    margin-top: 6px;
}
.phase-card-notes {
    font-size: 11px;
    color: #4b5563;
    margin-top: 4px;
}

/* legend */
.legend-box {
    margin-top: 12px;
    background: #ffffff;
    border-radius: 12px;
    padding: 8px 12px;
    box-shadow: 0 4px 10px rgba(15,23,42,0.08);
    font-size: 11px;
}
.legend-item {
    display: inline-flex;
    align-items: center;
    margin-right: 14px;
}
.legend-dot {
    width: 11px;
    height: 11px;
    border-radius: 999px;
    margin-right: 6px;
}

/* responsive tweak */
@media (max-width: 1100px) {
    .overview-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 780px) {
    .overview-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""


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
        st.markdown("<p class='big-label'>STEPS</p>", unsafe_allow_html=True)

    with c2:
        txt = f"{avg_success}%" if avg_success is not None else "—"
        st.markdown(f"<p class='big-metric'>{txt}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>AVG SUCCESS</p>", unsafe_allow_html=True)

    with c3:
        st.markdown(f"<p class='big-metric'>{active_steps}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>ACTIVE</p>", unsafe_allow_html=True)


# ------------------------------------------------------
# OVERVIEW VISUALS
# ------------------------------------------------------
def render_phase_chevrons():
    html = '<div class="chevron-row">'
    for phase in PHASES:
        html += f'<div class="chevron">{PHASE_SHORT[phase]}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def get_nodes_by_phase(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {p: [] for p in PHASES}
    for n in data.get("nodes", []):
        p = n.get("phase")
        if p in result:
            result[p].append(n)
    return result


def render_overview_grid(data: Dict[str, Any]):
    by_phase = get_nodes_by_phase(data)
    html = '<div class="overview-grid">'
    for phase in PHASES:
        html += '<div class="phase-column">'
        html += f'<div class="phase-column-label">{PHASE_SHORT[phase]}</div>'
        for node in by_phase.get(phase, []):
            label = node.get("label", "")
            time_est = node.get("time_estimate", "")
            success = node.get("success_rate", "")
            volume = node.get("volume_pct", "")
            path = node.get("path") or DEFAULT_PATH
            color = PATH_COLORS.get(path, "#9ca3af")
            status = node.get("status", "")

            tooltip_lines = [
                f"Phase: {phase}",
                f"Path: {path}",
                f"Status: {status or 'N/A'}",
                f"Time: {time_est or 'N/A'}",
                f"Success: {success or 'N/A'}",
                f"Volume: {volume or 'N/A'}%",
            ]
            tooltip = "&#10;".join(tooltip_lines)

            meta_bits = []
            if time_est:
                meta_bits.append(time_est)
            if success:
                meta_bits.append(f"{success} success")
            if volume not in ("", None):
                meta_bits.append(f"{volume}% volume")
            meta = " · ".join(meta_bits)

            html += f"""
            <div class="step-card" title="{tooltip}">
              <div class="path-pill" style="background:{color};">{path}</div>
              <div class="step-card-header">
                <div class="step-badge">STEP {node.get('id','')}</div>
                <div class="step-title">{label}</div>
              </div>
              <div class="step-sub">{phase}</div>
              <div class="step-meta">{meta}</div>
            </div>
            """
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_path_legend(data: Dict[str, Any]):
    counts = {p: 0 for p in PATH_COLORS}
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
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------
# PHASE DETAIL VIEW
# ------------------------------------------------------
def get_nodes_for_phase(data: Dict[str, Any], phase: str) -> List[Dict[str, Any]]:
    return [n for n in data.get("nodes", []) if n.get("phase") == phase]


def render_phase_cards(nodes: List[Dict[str, Any]]):
    html = ""
    for node in nodes:
        label = node.get("label", "")
        path = node.get("path") or DEFAULT_PATH
        color = PATH_COLORS.get(path, "#9ca3af")
        time_est = node.get("time_estimate", "")
        success = node.get("success_rate", "")
        volume = node.get("volume_pct", "")
        status = node.get("status", "")
        owner = node.get("owner", "")
        notes = node.get("notes", "")

        meta_bits = []
        if time_est:
            meta_bits.append(time_est)
        if success:
            meta_bits.append(f"{success} success")
        if volume not in ("", None):
            meta_bits.append(f"{volume}% volume")
        meta = " · ".join(meta_bits)

        html += f"""
        <div class="phase-card">
          <div class="phase-card-header">
            <div>
              <div class="phase-card-phase">{node.get('phase','').upper()}</div>
              <div class="phase-card-title">{label}</div>
            </div>
            <div style="font-size:11px; color:#4b5563;">
              <span style="display:inline-flex; align-items:center;">
                <span style="width:11px;height:11px;border-radius:999px;background:{color};margin-right:6px;"></span>
                {path}
              </span>
            </div>
          </div>
          <div class="phase-card-meta">
            Status: {status or 'N/A'} &nbsp;·&nbsp; Owner: {owner or 'N/A'} &nbsp;·&nbsp; {meta}
          </div>
          <div class="phase-card-notes">
            {notes or '<span style="color:#9ca3af;">No notes yet.</span>'}
          </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


def render_node_editor(data: Dict[str, Any], phase: str):
    all_nodes = data.get("nodes", [])
    phase_nodes = get_nodes_for_phase(data, phase)

    st.subheader("Edit step in this phase")

    if not phase_nodes:
        st.info("No steps in this phase.")
        return

    labels = [f"{n['id']}. {n['label']}" for n in phase_nodes]
    idx_in_phase = st.selectbox("Select step", range(len(phase_nodes)), format_func=lambda i: labels[i])
    node = phase_nodes[idx_in_phase]

    # locate in global list
    global_index = next(i for i, n in enumerate(all_nodes) if n["id"] == node["id"])

    st.markdown("### Basic Info")
    all_nodes[global_index]["label"] = st.text_input("Title", node.get("label", ""))

    all_nodes[global_index]["phase"] = st.selectbox(
        "Phase",
        PHASES,
        index=PHASES.index(node.get("phase", phase)) if node.get("phase", phase) in PHASES else PHASES.index(phase),
    )

    all_nodes[global_index]["path"] = st.selectbox(
        "Path (branch)",
        list(PATH_COLORS.keys()),
        index=list(PATH_COLORS.keys()).index(node.get("path", DEFAULT_PATH))
        if node.get("path", DEFAULT_PATH) in PATH_COLORS
        else 0,
    )

    all_nodes[global_index]["description"] = st.text_area(
        "Description",
        node.get("description", ""),
        height=90,
    )

    st.markdown("### Metrics")
    c1, c2, c3 = st.columns(3)
    with c1:
        all_nodes[global_index]["time_estimate"] = st.text_input(
            "Time Estimate",
            node.get("time_estimate", ""),
        )
    with c2:
        all_nodes[global_index]["volume_pct"] = st.number_input(
            "Volume %",
            value=float(node.get("volume_pct", 100) or 100),
            min_value=0.0,
            max_value=100.0,
            step=1.0,
        )
    with c3:
        all_nodes[global_index]["success_rate"] = st.text_input(
            "Success Rate (%)",
            str(node.get("success_rate", "")),
        )

    st.markdown("### Ownership & Notes")
    all_nodes[global_index]["owner"] = st.text_input("Owner", node.get("owner", ""))
    all_nodes[global_index]["status"] = st.selectbox(
        "Status",
        ["Planned", "In progress", "Blocked", "Completed"],
        index=["Planned", "In progress", "Blocked", "Completed"].index(node.get("status", "Planned")),
    )
    all_nodes[global_index]["notes"] = st.text_area("Notes", node.get("notes", ""), height=80)

    st.markdown("### Links")
    links_text = "\n".join(node.get("links", []))
    updated_links = st.text_area("Links (one per line)", value=links_text)
    all_nodes[global_index]["links"] = [l.strip() for l in updated_links.splitlines() if l.strip()]

    st.markdown("### Attachments")
    attachments = node.get("attachments", [])
    if attachments:
        st.caption("Existing files (paths):")
        for f in attachments:
            st.write("- " + f)

    uploaded = st.file_uploader("Upload files", accept_multiple_files=True, key=f"uploads_{phase}")
    for f in uploaded:
        step_dir = ATT_DIR / f"step_{node['id']}"
        step_dir.mkdir(parents=True, exist_ok=True)
        file_path = step_dir / f.name
        with file_path.open("wb") as out:
            out.write(f.getbuffer())
        attachments.append(str(file_path.relative_to(BASE_DIR)))
    all_nodes[global_index]["attachments"] = attachments


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

    # Summary page
    y = height - 30 * mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(25 * mm, y, title)

    y -= 10 * mm
    c.setFont("Helvetica", 11)
    c.drawString(25 * mm, y, data.get("description", ""))

    y -= 15 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, f"Steps: {total_steps}")
    c.drawString(70 * mm, y, f"Active: {active_steps}")
    avg_txt = f"{avg_success}%" if avg_success is not None else "—"
    c.drawString(120 * mm, y, f"Avg success: {avg_txt}")

    # Phase bar
    y -= 20 * mm
    phase_width = (width - 50 * mm) / len(PHASES)
    c.setFont("Helvetica-Bold", 9)
    for i, phase in enumerate(PHASES):
        x = 25 * mm + i * phase_width
        c.setFillColorRGB(1, 0.91, 0.6)
        c.rect(x, y, phase_width - 4, 10 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(x + (phase_width - 4) / 2, y + 3.5 * mm, PHASE_SHORT[phase])

    # Quick steps list
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
        # Detailed per phase
        for phase in PHASES:
            nodes = get_nodes_for_phase(data, phase)
            if not nodes:
                continue
            c.showPage()
            y = height - 30 * mm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(25 * mm, y, phase)
            y -= 10 * mm
            for node in nodes:
                if y < 30 * mm:
                    c.showPage()
                    y = height - 25 * mm
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(25 * mm, y, f"{phase} (cont.)")
                    y -= 8 * mm
                c.setFont("Helvetica-Bold", 11)
                c.drawString(25 * mm, y, f"Step {node.get('id','')} – {node.get('label','')}")
                y -= 5 * mm
                c.setFont("Helvetica", 9)
                c.drawString(
                    25 * mm,
                    y,
                    f"Owner: {node.get('owner','N/A')} · Status: {node.get('status','N/A')} · Path: {node.get('path',DEFAULT_PATH)}",
                )
                y -= 5 * mm
                c.drawString(
                    25 * mm,
                    y,
                    f"Time: {node.get('time_estimate','N/A')} · Success: {node.get('success_rate','N/A')} · Volume: {node.get('volume_pct','N/A')}%",
                )
                y -= 6 * mm
                desc = node.get("description", "") or "No description."
                c.drawString(25 * mm, y, f"Description: {desc}")
                y -= 8 * mm

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
    st.caption("Clean report-style overview of your launch journey, structured by phase and path.")

    # Sidebar — launch files
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

    # Tabs per view
    overview_tab, p1_tab, p2_tab, p3_tab, p4_tab = st.tabs(
        ["Overview", "Pilot & Initiate", "Prepare & Startup", "Execute & Adopt", "Close & Sustain"]
    )

    with overview_tab:
        st.subheader("Journey Overview")
        render_phase_chevrons()
        render_overview_grid(data)
        render_path_legend(data)

        st.markdown("### Export as PDF")
        if not REPORTLAB_AVAILABLE:
            st.warning("PDF export requires the 'reportlab' package. Add `reportlab` to requirements.txt.")
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

        with st.expander("Steps (table)"):
            st.dataframe(pd.DataFrame(data.get("nodes", [])))

    with p1_tab:
        left, right = st.columns([2.1, 1.9])
        with left:
            st.subheader("Pilot & Initiate – steps")
            render_phase_cards(get_nodes_for_phase(data, "Pilot & Initiate"))
        with right:
            render_node_editor(data, "Pilot & Initiate")

    with p2_tab:
        left, right = st.columns([2.1, 1.9])
        with left:
            st.subheader("Prepare & Startup – steps")
            render_phase_cards(get_nodes_for_phase(data, "Prepare & Startup"))
        with right:
            render_node_editor(data, "Prepare & Startup")

    with p3_tab:
        left, right = st.columns([2.1, 1.9])
        with left:
            st.subheader("Execute & Adopt – steps")
            render_phase_cards(get_nodes_for_phase(data, "Execute & Adopt"))
        with right:
            render_node_editor(data, "Execute & Adopt")

    with p4_tab:
        left, right = st.columns([2.1, 1.9])
        with left:
            st.subheader("Close & Sustain – steps")
            render_phase_cards(get_nodes_for_phase(data, "Close & Sustain"))
        with right:
            render_node_editor(data, "Close & Sustain")


if __name__ == "__main__":
    main()
