import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple

import streamlit as st

# PDF support (optional but recommended)
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


# -------------------------------------------------------------------
# CONFIG & CONSTANTS
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Global Launch Navigator",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🧭",
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "default_flow.json"

PHASES = [
    "Pilot & Initiate",
    "Prepare & Startup",
    "Execute & Adopt",
    "Close & Sustain",
]

PATH_VARIANTS = ["Primary", "Data Prep", "Enhanced", "Exit"]

PATH_COLORS = {
    "Primary": "#10b981",   # emerald
    "Data Prep": "#f97316", # orange
    "Enhanced": "#6366f1",  # indigo
    "Exit": "#ef4444",      # red
}

PHASE_COLORS = {
    "Pilot & Initiate": "#FFEFB0",
    "Prepare & Startup": "#FFE9A3",
    "Execute & Adopt":  "#FFE7A1",
    "Close & Sustain":  "#FFE5A0",
}


THEMES = {
    "Nordic Blue": {
        "bg": "#f4f4f7",
        "accent": "#1d4ed8",
        "accent_soft": "#e0ebff",
        "text": "#111827",
    },
    "Graphite": {
        "bg": "#f3f3f3",
        "accent": "#111827",
        "accent_soft": "#e5e7eb",
        "text": "#111827",
    },
    "Emerald": {
        "bg": "#f3f7f5",
        "accent": "#059669",
        "accent_soft": "#dcfce7",
        "text": "#052e16",
    },
}


# -------------------------------------------------------------------
# DATA HELPERS
# -------------------------------------------------------------------
def default_flow() -> Dict[str, Any]:
    """Fallback demo flow, used if file missing or malformed."""
    steps = [
        # Phase 1
        dict(
            title="Assess launch and secure awareness",
            phase="Pilot & Initiate",
            description="Clarify objectives, scope, and high-level success metrics.",
            timeline="1–2w",
            volume=5,
            success=95,
            path="Primary",
        ),
        dict(
            title="Central launch preparations",
            phase="Pilot & Initiate",
            description="Align global stakeholders and prepare core materials.",
            timeline="2–3w",
            volume=10,
            success=92,
            path="Primary",
        ),
        dict(
            title="Pilot solution",
            phase="Pilot & Initiate",
            description="Run a limited pilot with a representative set of countries/sites.",
            timeline="3–4w",
            volume=10,
            success=90,
            path="Enhanced",
        ),
        # Phase 2
        dict(
            title="Prepare for global rollout",
            phase="Prepare & Startup",
            description="Finalize business case and deployment plan based on pilot learnings.",
            timeline="2–3w",
            volume=20,
            success=93,
            path="Primary",
        ),
        dict(
            title="Introduce launch and prioritize",
            phase="Prepare & Startup",
            description="Prioritize markets and define rollout waves.",
            timeline="1–2w",
            volume=20,
            success=90,
            path="Data Prep",
        ),
        dict(
            title="Agree on ambition & timeline",
            phase="Prepare & Startup",
            description="Confirm ambition level and timelines with key stakeholders.",
            timeline="1–2w",
            volume=20,
            success=92,
            path="Primary",
        ),
        # Phase 3
        dict(
            title="Plan launch and adoption",
            phase="Execute & Adopt",
            description="Plan communication, training, and adoption activities.",
            timeline="3–6w",
            volume=80,
            success=90,
            path="Primary",
        ),
        dict(
            title="Deliver and adopt solution",
            phase="Execute & Adopt",
            description="Deploy solution to markets and monitor adoption.",
            timeline="6–12w",
            volume=80,
            success=88,
            path="Primary",
        ),
        # Phase 4
        dict(
            title="Handover and close country launch",
            phase="Close & Sustain",
            description="Transition to run-organization and confirm handover criteria.",
            timeline="2–4w",
            volume=100,
            success=95,
            path="Primary",
        ),
        dict(
            title="Follow up on value and adoption",
            phase="Close & Sustain",
            description="Validate realized value and capture lessons learned.",
            timeline="4–6w",
            volume=100,
            success=93,
            path="Enhanced",
        ),
        dict(
            title="Close launch initiative",
            phase="Close & Sustain",
            description="Formal closure, governance update, and documentation.",
            timeline="1–2w",
            volume=100,
            success=97,
            path="Primary",
        ),
    ]
    # add ids & order
    for i, s in enumerate(steps):
        s["id"] = str(uuid.uuid4())
        s["order"] = i
        s.setdefault("owner", "")
        s.setdefault("status", "Planned")
    return {"steps": steps}


def load_flow() -> Dict[str, Any]:
    """Load flow from JSON. Convert older 'nodes' structure if needed."""
    if not DATA_FILE.exists():
        return default_flow()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return default_flow()

    # Support old schema with "nodes"
    if isinstance(raw, dict) and "steps" in raw:
        data = {"steps": list(raw["steps"])}
    elif isinstance(raw, dict) and "nodes" in raw:
        steps = []
        for n in raw["nodes"]:
            steps.append(
                dict(
                    id=str(n.get("id", uuid.uuid4())),
                    title=n.get("label", "Unnamed step"),
                    phase=n.get("phase", PHASES[0]),
                    description=n.get("description", ""),
                    timeline=n.get("time_estimate", ""),
                    volume=n.get("volume_pct", 0),
                    success=float(str(n.get("success_rate", 0)).replace("%", "") or 0),
                    path=n.get("path", "Primary"),
                    owner=n.get("owner", ""),
                    status=n.get("status", "Planned"),
                    order=n.get("order", 0),
                )
            )
        data = {"steps": steps}
    else:
        # Unknown structure, fallback
        return default_flow()

    normalize_flow(data)
    return data


def save_flow(data: Dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_flow(data: Dict[str, Any]) -> None:
    """Ensure IDs, orders, defaults."""
    steps = data.get("steps", [])
    # assign ids
    for s in steps:
        if "id" not in s:
            s["id"] = str(uuid.uuid4())
        if "phase" not in s or s["phase"] not in PHASES:
            s["phase"] = PHASES[0]
        if "path" not in s or s["path"] not in PATH_VARIANTS:
            s["path"] = "Primary"
        s.setdefault("timeline", "")
        s.setdefault("volume", 0)
        s.setdefault("success", 0)
        s.setdefault("owner", "")
        s.setdefault("status", "Planned")
    # assign order within phase if missing
    for phase in PHASES:
        phase_steps = [s for s in steps if s["phase"] == phase]
        phase_steps_sorted = sorted(
            phase_steps, key=lambda x: x.get("order", 9999)
        )
        for i, s in enumerate(phase_steps_sorted):
            s["order"] = i
    # sort steps by (phase, order)
    steps.sort(
        key=lambda s: (
            PHASES.index(s["phase"]) if s["phase"] in PHASES else 999,
            s.get("order", 0),
        )
    )
    data["steps"] = steps


def get_flow() -> Dict[str, Any]:
    if "flow" not in st.session_state:
        st.session_state["flow"] = load_flow()
    return st.session_state["flow"]


def set_flow(flow: Dict[str, Any]) -> None:
    st.session_state["flow"] = flow


# -------------------------------------------------------------------
# THEMES & CSS
# -------------------------------------------------------------------
def apply_theme(theme_name: str) -> None:
    theme = THEMES[theme_name]
    bg = theme["bg"]
    accent = theme["accent"]
    accent_soft = theme["accent_soft"]
    text = theme["text"]

    css = f"""
    <style>
    :root {{
        --accent: {accent};
        --accent-soft: {accent_soft};
        --bg: {bg};
        --text: {text};
    }}

    .stApp {{
        background-color: var(--bg);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    /* top cards */
    .metric-card {{
        background: white;
        padding: 16px 18px;
        border-radius: 14px;
        box-shadow: 0 8px 20px rgba(15,23,42,0.08);
        border: 1px solid #e5e7eb;
    }}
    .metric-label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
    }}
    .metric-value {{
        font-size: 30px;
        font-weight: 700;
        margin-top: 4px;
        color: #111827;
    }}

    /* flow ribbon background */
    .flow-wrapper {{
        position: relative;
        padding: 32px 24px;
        border-radius: 24px;
        overflow: hidden;
        background: radial-gradient(circle at 0% 0%, #ffffff, #f9fafb 40%, #e5e7eb 100%);
    }}

    .flow-ribbon {{
        position: absolute;
        inset: 0;
        background: linear-gradient(120deg,
            rgba(148, 163, 184, 0.18),
            rgba(79, 70, 229, 0.08),
            rgba(16, 185, 129, 0.16));
        background-size: 200% 200%;
        animation: flowMove 25s ease-in-out infinite;
        opacity: 0.5;
    }}

    @keyframes flowMove {{
        0%   {{ background-position: 0% 50%; }}
        50%  {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    .flow-content {{
        position: relative;
    }}

    .phase-header {{
        display: inline-block;
        padding: 10px 22px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: #111827;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }}

    .phase-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        margin-bottom: 18px;
    }}

    .step-card {{
        flex: 1 1 230px;
        max-width: 320px;
        background: #f9fafb;
        border-radius: 16px;
        padding: 14px 14px 12px 14px;
        box-shadow: 0 10px 25px rgba(15,23,42,0.12);
        border: 1px solid rgba(148,163,184,0.35);
        position: relative;
        overflow: hidden;
        transition: transform 0.12s ease-out, box-shadow 0.12s ease-out;
    }}

    .step-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 14px 28px rgba(15,23,42,0.16);
    }}

    .step-path-pill {{
        position: absolute;
        right: 10px;
        top: 10px;
        font-size: 10px;
        padding: 2px 9px;
        border-radius: 999px;
        color: white;
        background: #6b7280;
    }}

    .step-title {{
        font-size: 14px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 4px;
    }}

    .step-meta {{
        font-size: 11px;
        color: #6b7280;
    }}

    .step-desc {{
        font-size: 11px;
        color: #4b5563;
        margin-top: 6px;
    }}

    .legend-pill {{
        display:inline-flex;
        align-items:center;
        padding:4px 8px;
        border-radius:999px;
        background:white;
        box-shadow:0 2px 6px rgba(15,23,42,0.08);
        font-size:11px;
        margin-right:8px;
        margin-bottom:6px;
    }}

    .legend-dot {{
        width:12px;
        height:12px;
        border-radius:999px;
        margin-right:6px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# -------------------------------------------------------------------
# METRICS / ANALYTICS
# -------------------------------------------------------------------
def compute_metrics(flow: Dict[str, Any]) -> Tuple[int, float, float]:
    steps = flow.get("steps", [])
    total = len(steps)
    avg_success = (
        sum([float(s.get("success", 0)) for s in steps]) / total if total else 0
    )
    avg_volume = (
        sum([float(s.get("volume", 0)) for s in steps]) / total if total else 0
    )
    return total, avg_success, avg_volume


def metrics_block(flow: Dict[str, Any]) -> None:
    total, avg_success, avg_volume = compute_metrics(flow)
    c1, c2, c3 = st.columns(3)
    for col, label, value in [
        (c1, "Steps", total),
        (c2, "Avg Success %", f"{avg_success:.1f}"),
        (c3, "Avg Volume %", f"{avg_volume:.1f}"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# -------------------------------------------------------------------
# FLOW MAP (VIEW MODE)
# -------------------------------------------------------------------
def flow_map(flow: Dict[str, Any]) -> None:
    steps = flow.get("steps", [])
    st.markdown("### Journey Overview")

    st.markdown('<div class="flow-wrapper"><div class="flow-ribbon"></div><div class="flow-content">', unsafe_allow_html=True)

    # per phase
    for phase in PHASES:
        phase_steps = [s for s in steps if s["phase"] == phase]
        if not phase_steps:
            continue

        st.markdown(
            f'<div class="phase-header">{phase}</div>', unsafe_allow_html=True
        )
        st.markdown('<div class="phase-row">', unsafe_allow_html=True)

        for s in phase_steps:
            path = s.get("path", "Primary")
            color = PATH_COLORS.get(path, "#6b7280")
            meta = f'{s.get("timeline","")} · {s.get("volume",0)}% volume · {s.get("success",0)}% success'
            tooltip = (
                f"Owner: {s.get('owner','N/A')} | Status: {s.get('status','N/A')}"
            )

            st.markdown(
                f"""
                <div class="step-card" title="{tooltip}">
                    <div class="step-path-pill" style="background:{color};">
                        {path}
                    </div>
                    <div class="step-title">{s["title"]}</div>
                    <div class="step-meta">{meta}</div>
                    <div class="step-desc">{s.get("description","")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Legend
    st.markdown("#### Legend")
    legend_html = ""
    for name, color in PATH_COLORS.items():
        legend_html += f"""
        <span class="legend-pill">
            <span class="legend-dot" style="background:{color};"></span>
            {name}
        </span>
        """
    st.markdown(legend_html, unsafe_allow_html=True)


# -------------------------------------------------------------------
# PHASE VIEW + HYBRID EDITOR
# -------------------------------------------------------------------
def phase_view(flow: Dict[str, Any], phase: str) -> None:
    steps = [s for s in flow["steps"] if s["phase"] == phase]
    st.subheader(f"{phase} — overview")

    for s in steps:
        path_color = PATH_COLORS.get(s.get("path", "Primary"), "#6b7280")
        meta = f'{s.get("timeline","")} · {s.get("volume",0)}% · {s.get("success",0)}%'
        with st.container(border=True):
            # viewer
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                  <div>
                    <div style="font-size:18px;font-weight:600;">{s["title"]}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:2px;">{phase} · {s.get("path","Primary")}</div>
                    <div style="font-size:13px;color:#4b5563;margin-top:6px;">{s.get("description","")}</div>
                    <div style="font-size:12px;color:#4b5563;margin-top:6px;">{meta}</div>
                  </div>
                  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;margin-left:16px;">
                    <div style="width:14px;height:14px;border-radius:999px;background:{path_color};"></div>
                    <div style="font-size:11px;color:#6b7280;">{s.get("status","Planned")}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Edit this step"):
                edit_step(flow, s)


def edit_step(flow: Dict[str, Any], step: Dict[str, Any]) -> None:
    """Hybrid inline editor – unique keys based on id."""
    step_id = step["id"]
    idx = next(i for i, s in enumerate(flow["steps"]) if s["id"] == step_id)
    s = flow["steps"][idx]

    s["title"] = st.text_input(
        "Title",
        value=s["title"],
        key=f"title_{step_id}",
    )
    s["description"] = st.text_area(
        "Description",
        value=s.get("description", ""),
        key=f"desc_{step_id}",
        height=90,
    )

    col1, col2 = st.columns(2)
    with col1:
        s["phase"] = st.selectbox(
            "Phase",
            PHASES,
            index=PHASES.index(s["phase"])
            if s["phase"] in PHASES
            else 0,
            key=f"phase_{step_id}",
        )
        s["path"] = st.selectbox(
            "Path (branch)",
            PATH_VARIANTS,
            index=PATH_VARIANTS.index(s.get("path", "Primary"))
            if s.get("path", "Primary") in PATH_VARIANTS
            else 0,
            key=f"path_{step_id}",
        )
        s["timeline"] = st.text_input(
            "Timeline",
            value=s.get("timeline", ""),
            key=f"time_{step_id}",
        )
    with col2:
        s["volume"] = st.number_input(
            "Volume %",
            value=int(s.get("volume", 0)),
            min_value=0,
            max_value=100,
            step=1,
            key=f"volume_{step_id}",
        )
        s["success"] = st.number_input(
            "Success %",
            value=int(s.get("success", 0)),
            min_value=0,
            max_value=100,
            step=1,
            key=f"success_{step_id}",
        )
        s["status"] = st.selectbox(
            "Status",
            ["Planned", "In progress", "Blocked", "Completed"],
            index=["Planned", "In progress", "Blocked", "Completed"].index(
                s.get("status", "Planned")
            ),
            key=f"status_{step_id}",
        )
    s["owner"] = st.text_input(
        "Owner",
        value=s.get("owner", ""),
        key=f"owner_{step_id}",
    )

    flow["steps"][idx] = s
    set_flow(flow)


# -------------------------------------------------------------------
# REORDER (pseudo drag & drop)
# -------------------------------------------------------------------
def reorder_page(flow: Dict[str, Any]) -> None:
    st.subheader("Reorder steps (click arrows to move cards)")

    for phase in PHASES:
        st.markdown(f"#### {phase}")
        phase_steps = [s for s in flow["steps"] if s["phase"] == phase]
        phase_steps = sorted(phase_steps, key=lambda s: s.get("order", 0))

        for s in phase_steps:
            step_id = s["id"]
            order = s.get("order", 0)

            col1, col2, col3 = st.columns([0.1, 0.1, 0.8])
            with col1:
                if st.button("↑", key=f"up_{step_id}"):
                    s["order"] = max(0, order - 1)
            with col2:
                if st.button("↓", key=f"down_{step_id}"):
                    s["order"] = order + 1
            with col3:
                st.write(f"**{s['title']}**  \n_{phase}_  · order: {s['order']}")

        st.markdown("---")

    normalize_flow(flow)
    set_flow(flow)
    if st.button("Save order to file"):
        save_flow(flow)
        st.success("Order saved.")


# -------------------------------------------------------------------
# PDF EXPORT
# -------------------------------------------------------------------
def export_pdf(flow: Dict[str, Any]) -> None:
    if not REPORTLAB_AVAILABLE:
        st.warning(
            "PDF export requires the 'reportlab' package in requirements.txt."
        )
        return

    filename = "launch_navigator_report.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Global Launch Navigator", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))

    total, avg_success, avg_volume = compute_metrics(flow)
    story.append(
        Paragraph(f"Total steps: {total}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Average success: {avg_success:.1f}%", styles["Normal"])
    )
    story.append(
        Paragraph(f"Average volume: {avg_volume:.1f}%", styles["Normal"])
    )
    story.append(Spacer(1, 0.3 * inch))

    for phase in PHASES:
        story.append(Paragraph(phase, styles["Heading2"]))
        story.append(Spacer(1, 0.15 * inch))
        phase_steps = [
            s for s in flow["steps"] if s["phase"] == phase
        ]
        for s in phase_steps:
            story.append(Paragraph(s["title"], styles["Heading4"]))
            story.append(
                Paragraph(
                    s.get("description", ""), styles["BodyText"]
                )
            )
            meta = (
                f"Timeline: {s.get('timeline','')} "
                f"· Volume: {s.get('volume',0)}% "
                f"· Success: {s.get('success',0)}% "
                f"· Path: {s.get('path','Primary')}"
            )
            story.append(Paragraph(meta, styles["BodyText"]))
            story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.25 * inch))

    doc.build(story)

    with open(filename, "rb") as f:
        st.download_button(
            "📄 Download PDF report",
            f,
            file_name=filename,
            mime="application/pdf",
        )


# -------------------------------------------------------------------
# MAIN APP
# -------------------------------------------------------------------
def main() -> None:
    # Theme selection (sidebar)
    with st.sidebar:
        st.title("📘 Global Launch Navigator")
        theme_name = st.selectbox(
            "Theme",
            list(THEMES.keys()),
            index=list(THEMES.keys()).index("Nordic Blue"),
        )
    apply_theme(theme_name)

    flow = get_flow()
    normalize_flow(flow)

    # Navigation
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "",
            ["Overview"] + PHASES + ["Reorder", "Export PDF"],
        )
        if st.button("💾 Save to JSON"):
            save_flow(flow)
            st.success("Saved to data/default_flow.json")

    st.title("🧭 Global Launch Navigator")

    # Pages
    if page == "Overview":
        metrics_block(flow)
        st.markdown("---")
        flow_map(flow)

    elif page in PHASES:
        phase_view(flow, page)

    elif page == "Reorder":
        reorder_page(flow)

    elif page == "Export PDF":
        export_pdf(flow)


if __name__ == "__main__":
    main()
