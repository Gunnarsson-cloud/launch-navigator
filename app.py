import json
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ATT_DIR = DATA_DIR / "attachments"

DATA_DIR.mkdir(exist_ok=True)
ATT_DIR.mkdir(exist_ok=True)


DEFAULT_FILE = DATA_DIR / "default_flow.json"


# ------------------------------------------------------
# STYLE
# ------------------------------------------------------
PAGE_CSS = """
<style>
.big-metric {
    font-size: 28px;
    font-weight: 700;
}
.big-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #555;
    margin-top: -6px;
}
.stApp {
    background-color: #f5f5f7;
}
</style>
"""


PHASE_COLORS = {
    "Pilot & Initiate": "rgba(230, 236, 245, 0.8)",
    "Prepare & Startup": "rgba(230, 245, 240, 0.8)",
    "Execute & Adopt": "rgba(244, 234, 245, 0.8)",
    "Close & Sustain": "rgba(245, 240, 230, 0.8)",
}


# ------------------------------------------------------
# FILE HELPERS
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
# SANKEY DIAGRAM
# ------------------------------------------------------
def build_sankey(data: Dict[str, Any]):
    nodes = data["nodes"]
    labels = [n["label"] for n in nodes]

    sources = []
    targets = []
    values = []
    colors = []

    # Simple linear flow
    for i in range(len(nodes) - 1):
        sources.append(i)
        targets.append(i + 1)
        values.append(nodes[i + 1].get("volume_pct", 100))
        colors.append("rgba(180,180,190,0.35)")

    node_colors = [
        PHASE_COLORS.get(n["phase"], "rgba(220,220,220,0.7)")
        for n in nodes
    ]

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=40,
                    thickness=28,
                    label=labels,
                    color=node_colors,
                    line=dict(color="rgba(0,0,0,0.1)", width=1),
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=colors,
                ),
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Helvetica, Arial, sans-serif", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    return fig


# ------------------------------------------------------
# METRICS HEADER
# ------------------------------------------------------
def render_metrics(data: Dict[str, Any]):
    nodes = data["nodes"]

    total_steps = len(nodes)
    active_steps = sum(1 for n in nodes if n.get("status") in ["In progress", "Planned"])

    success_values = []
    for n in nodes:
        raw = str(n.get("success_rate", "")).replace("%", "").strip()
        try:
            success_values.append(float(raw))
        except:
            pass

    avg_success = round(sum(success_values) / len(success_values), 1) if success_values else None

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"<p class='big-metric'>{total_steps}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Steps</p>", unsafe_allow_html=True)

    with c2:
        s = f"{avg_success}%" if avg_success else "—"
        st.markdown(f"<p class='big-metric'>{s}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Avg Success</p>", unsafe_allow_html=True)

    with c3:
        st.markdown(f"<p class='big-metric'>{active_steps}</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-label'>Active</p>", unsafe_allow_html=True)


# ------------------------------------------------------
# NODE EDITOR
# ------------------------------------------------------
def render_node_editor(data: Dict[str, Any]):
    nodes = data["nodes"]

    st.subheader("Step Details Editor")

    labels = [f"{n['id']}. {n['label']}" for n in nodes]
    idx = st.selectbox("Select step", range(len(nodes)), format_func=lambda i: labels[i])
    node = nodes[idx]

    st.markdown("### Basic Info")
    node["label"] = st.text_input("Title", node.get("label", ""))

    node["phase"] = st.selectbox(
        "Phase",
        list(PHASE_COLORS.keys()),
        index=list(PHASE_COLORS.keys()).index(node.get("phase", "Pilot & Initiate")),
    )

    node["description"] = st.text_area("Description", node.get("description", ""), height=120)

    st.markdown("### Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        node["time_estimate"] = st.text_input("Time Estimate", node.get("time_estimate", ""))
    with c2:
        node["volume_pct"] = st.number_input("Volume %", value=float(node.get("volume_pct", 100)))
    with c3:
        node["success_rate"] = st.text_input("Success Rate (%)", str(node.get("success_rate", "")))
    with c4:
        node["status"] = st.selectbox(
            "Status",
            ["Planned", "In progress", "Blocked", "Completed"],
            index=["Planned", "In progress", "Blocked", "Completed"].index(node.get("status", "Planned")),
        )

    st.markdown("### Ownership & Notes")
    c5, c6 = st.columns(2)
    with c5:
        node["owner"] = st.text_input("Owner", node.get("owner", ""))
    with c6:
        node["notes"] = st.text_area("Notes", node.get("notes", ""), height=80)

    st.markdown("### Links")
    links_text = "\n".join(node.get("links", []))
    updated = st.text_area("Links (one per line)", value=links_text)
    node["links"] = [l.strip() for l in updated.splitlines() if l.strip()]

    st.markdown("### Attachments")
    attachments = node.get("attachments", [])

    if attachments:
        st.caption("Existing files:")
        for f in attachments:
            st.write(f"- {f}")

    uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)

    for f in uploaded_files:
        step_dir = ATT_DIR / f"step_{node['id']}"
        step_dir.mkdir(parents=True, exist_ok=True)
        file_path = step_dir / f.name
        with file_path.open("wb") as out:
            out.write(f.getbuffer())
        attachments.append(str(file_path.relative_to(BASE_DIR)))

    node["attachments"] = attachments


# ------------------------------------------------------
# APP
# ------------------------------------------------------
def main():
    st.set_page_config(page_title="Global Launch Navigator", layout="wide", page_icon="🧭")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    st.title("🧭 Global Launch Navigator")
    st.caption("Editable launch flow with steps, metrics, attachments, and Sankey overview.")

    # --- Sidebar: File Management ---
    st.sidebar.header("Launch File")

    files = list_launch_files()
    if DEFAULT_FILE not in files:
        files.insert(0, DEFAULT_FILE)

    selected = st.sidebar.selectbox(
        "Select launch file",
        files,
        index=files.index(DEFAULT_FILE),
        format_func=lambda x: x.name
    )

    if "launch" not in st.session_state or st.session_state["file"] != str(selected):
        st.session_state["launch"] = load_launch(selected)
        st.session_state["file"] = str(selected)

    data = st.session_state["launch"]

    new_name = st.sidebar.text_input("Save As (filename.json)", value=selected.name)

    if st.sidebar.button("Save"):
        save_launch(data, DATA_DIR / new_name)
        st.sidebar.success(f"Saved as {new_name}")

    # --- Metrics ---
    render_metrics(data)

    st.markdown("---")

    # --- Diagram + Editor ---
    left, right = st.columns([2.2, 1.6])

    with left:
        st.subheader("Flow Overview")
        fig = build_sankey(data)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        render_node_editor(data)

    # --- Table ---
    with st.expander("Show steps as table"):
        df = pd.DataFrame(data["nodes"])
        st.dataframe(df)


if __name__ == "__main__":
    main()
