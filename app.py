import streamlit as st
import json
import uuid
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Global Launch Navigator",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path("data/default_flow.json")

PHASES = [
    "Pilot & Initiate",
    "Prepare & Startup",
    "Execute & Adopt",
    "Close & Sustain",
]

PHASE_COLORS = {
    "Pilot & Initiate": "#FFEFB0",
    "Prepare & Startup": "#FFE9A3",
    "Execute & Adopt": "#FFE7A1",
    "Close & Sustain": "#FFE59F",
}

PATH_COLORS = {
    "Primary": "#B7D4C5",
    "Alternative": "#E6C9A8",
    "Enhanced": "#C5B3D6",
    "Exit": "#D8A3A3"
}

DEFAULT_PATH = "Primary"


# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def load_flow():
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except:
        return {"steps": []}


def save_flow(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)


def ensure_ids(data):
    # Assign unique IDs to steps that do not yet have one
    for step in data["steps"]:
        if "id" not in step:
            step["id"] = str(uuid.uuid4())
    return data


# ------------------------------------------------------------
# UI COMPONENTS
# ------------------------------------------------------------
def draw_phase_header(title):
    st.markdown(
        f"""
        <div style="
            background: #111;
            padding: 18px;
            color: white;
            font-size: 26px;
            font-weight: 600;
            border-radius: 6px;">
            {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def step_card(step):
    """Mini step card for the phase pages."""
    bg = PHASE_COLORS.get(step["phase"], "#FFF")
    path_color = PATH_COLORS.get(step.get("path", DEFAULT_PATH), "#CCC")

    st.markdown(
        f"""
        <div style="
            background:{bg};
            padding:16px;
            border-radius:10px;
            margin-bottom:14px;
            border-left:6px solid {path_color};
        ">
            <div style="font-size:20px;font-weight:600;margin-bottom:6px;">
                {step['title']}
            </div>

            <div style="opacity:0.7;font-size:14px;margin-bottom:4px;">
                {step.get('description','')}
            </div>

            <div style="font-size:13px;color:#444;margin-top:8px;">
                ⏱ {step.get('timeline','')} &nbsp;•&nbsp;
                🔁 {step.get('volume',0)}% &nbsp;•&nbsp;
                🎯 {step.get('success',0)}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_flow_ribbons(data):
    """High-level flow visual (simplified McKinsey style)."""
    st.markdown("### End-to-End Flow Overview")

    for phase in PHASES:
        st.markdown(
            f"""
            <div style="
                background:{PHASE_COLORS[phase]};
                padding:22px;
                border-radius:8px;
                margin-top:12px;
                font-size:22px;
                font-weight:600;
            ">
                {phase}
            </div>
            """,
            unsafe_allow_html=True,
        )

        phase_steps = [s for s in data["steps"] if s["phase"] == phase]

        cols = st.columns(len(phase_steps) if phase_steps else 1)

        for col, step in zip(cols, phase_steps):
            with col:
                st.markdown(
                    f"""
                    <div style="
                        margin-top:10px;
                        background:white;
                        padding:14px;
                        border-radius:10px;
                        border-left:6px solid {PATH_COLORS.get(step.get("path", DEFAULT_PATH))};
                        box-shadow:0 2px 6px rgba(0,0,0,0.08);
                    ">
                        <div style="font-weight:600;font-size:16px;margin-bottom:6px;">
                            {step['title']}
                        </div>
                        <div style="opacity:0.7;font-size:13px;">
                            {step.get('description','')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def export_pdf(data):
    """Generate PDF report."""
    filename = "Launch_Navigator_Report.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Global Launch Navigator Report</b>", styles["Title"]))
    story.append(Spacer(1, 0.3 * inch))

    for phase in PHASES:
        story.append(Paragraph(f"<b>{phase}</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        steps = [s for s in data["steps"] if s["phase"] == phase]

        for step in steps:
            story.append(Paragraph(f"<b>{step['title']}</b>", styles["Heading4"]))
            story.append(Paragraph(step.get("description", ""), styles["BodyText"]))
            story.append(
                Paragraph(
                    f"Timeline: {step.get('timeline','')} &nbsp; "
                    f"Volume: {step.get('volume',0)}% &nbsp; "
                    f"Success: {step.get('success',0)}%",
                    styles["BodyText"],
                )
            )
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)

    with open(filename, "rb") as f:
        st.download_button("⬇️ Download PDF Report", f, file_name=filename)


# ------------------------------------------------------------
# SIDEBAR NAVIGATION
# ------------------------------------------------------------
st.sidebar.title("📘 Global Launch Navigator")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Pilot & Initiate", "Prepare & Startup", "Execute & Adopt", "Close & Sustain", "Export PDF"],
)

data = ensure_ids(load_flow())


# ------------------------------------------------------------
# PAGE: OVERVIEW
# ------------------------------------------------------------
if page == "Overview":
    st.title("🌍 Global Launch Navigator — Overview")
    st.write("Professional, balanced, clear view of the full journey.")

    render_flow_ribbons(data)

    st.markdown("---")
    st.subheader("Legend")
    for name, color in PATH_COLORS.items():
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;margin-bottom:6px;">
                <div style="background:{color};width:26px;height:14px;border-radius:3px;margin-right:8px;"></div>
                <div>{name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# PAGE: PHASE PAGES
# ------------------------------------------------------------
else:
    if page in PHASES:
        phase = page
        draw_phase_header(phase)

        steps = [s for s in data["steps"] if s["phase"] == phase]

        st.markdown("### Phase Steps")
        for step in steps:
            step_card(step)

        st.markdown("---")
        st.markdown("### Edit Steps")

        for idx, step in enumerate(steps):
            global_index = data["steps"].index(step)
            unique = f"{phase}_{global_index}"

            st.markdown(f"#### {step['title']}")

            data["steps"][global_index]["title"] = st.text_input(
                "Title", value=step["title"], key=f"{unique}_title"
            )
            data["steps"][global_index]["description"] = st.text_area(
                "Description", value=step.get("description",""), key=f"{unique}_desc"
            )
            data["steps"][global_index]["timeline"] = st.text_input(
                "Timeline", value=step.get("timeline",""), key=f"{unique}_timeline"
            )
            data["steps"][global_index]["volume"] = st.number_input(
                "Volume %", value=step.get("volume",0), min_value=0, max_value=100,
                key=f"{unique}_volume"
            )
            data["steps"][global_index]["success"] = st.number_input(
                "Success %", value=step.get("success",0), min_value=0, max_value=100,
                key=f"{unique}_success"
            )
            data["steps"][global_index]["path"] = st.selectbox(
                "Path (Branch)",
                list(PATH_COLORS.keys()),
                index=list(PATH_COLORS.keys()).index(step.get("path", DEFAULT_PATH)),
                key=f"{unique}_path",
            )

        if st.button("💾 Save changes"):
            save_flow(data)
            st.success("Saved!")


# ------------------------------------------------------------
# PAGE: PDF EXPORT
# ------------------------------------------------------------
if page == "Export PDF":
    st.title("📄 Export Professional PDF Report")
    export_pdf(data)
