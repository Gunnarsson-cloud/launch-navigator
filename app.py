import json
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


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
# STYLE / COLORS
# ------------------------------------------------------
PAGE_CSS = """
<style>
.stApp {
    background-color: #f7f7f9;
}
.big-metric {
    font-size: 30px;
    font-weight: 700;
}
.big-label {
    font-size: 12px;
    text-transform: uppercase;
    color: #666;
    margin-top: -6px;
}
</style>
"""

PHASE_COLORS = {
    "Pilot & Initiate": "rgba(240, 227, 220, 0.95)",
    "Prepare & Startup": "rgba(224, 237, 230, 0.95)",
    "Execute & Adopt": "rgba(230, 228, 241, 0.95)",
    "Close & Sustain": "rgba(242, 238, 220, 0.95)"
}


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
# PREMIUM CUSTOM SANKEY
# ------------------------------------------------------
def build_sankey(data: Dict[str, Any]):
    nodes = data["nodes"]
    n = len(nodes)

    # Volume → thickness
    volumes = []
    for n_node in nodes:
        try:
            v = float(n_node.get("volume_pct", 100) or 100)
        except Exception:
            v = 100.0
        volumes.append(max(v, 1.0))

    # Node positions
    xs = [0.05 + i * (0.9 / (n - 1)) for i in range(n)] if n > 1 else [0.5]
    ys = [0.5] * n

    # Simple L→R links
    sources = []
    targets = []
    values = []
    link_colors = []
    for i in range(n - 1):
        sources.append(i)
        targets.append(i + 1)
        values.append((volumes[i] + volumes[i + 1]) / 2)
        link_colors.append("rgba(160,160,175,0.35)")

    # Invisible base Sankey
    sankey = go.Sankey(
        arrangement="fixed",
        node=dict(
            pad=20,
            thickness=10,
            label=[""] * n,
            color=["rgba(0,0,0,0)"] * n,
            line=dict(color="rgba(0,0,0,0)", width=0),
            x=xs,
            y=ys,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
    )

    fig = go.Figure(data=[sankey])

    # Custom node cards
    shapes = []
    annotations = []

    card_width = 0.12
    card_height = 0.45
    y_center = 0.5
    y0 = y_center - card_height / 2
    y1 = y_center + card_height / 2
    phase_band_height = 0.10

    for i, node in enumerate(nodes):
        x_center = xs[i]
        x0 = x_center - card_width / 2
        x1 = x_center + card_width / 2

        # Card background
        shapes.append(dict(
            type="rect",
            xref="paper", yref="paper",
            x0=x0, x1=x1, y0=y0, y1=y1,
            line=dict(color="rgba(0,0,0,0.15)", width=1.2),
            fillcolor="rgba(255,255,255,0.97)",
            layer="above"
        ))

        # Phase color band
        phase_color = PHASE_COLORS.get(node.get("phase", ""), "rgba(230,230,230,0.95)")
        shapes.append(dict(
            type="rect",
            xref="paper", yref="paper",
            x0=x0, x1=x1, y0=y1-phase_band_height, y1=y1,
            fillcolor=phase_color,
            line=dict(color="rgba(0,0,0,0)", width=0),
            layer="above"
        ))

        # Phase text
        annotations.append(dict(
            x=x_center, y=y1 - phase_band_height/2,
            xref="paper", yref="paper",
            text=node.get("phase", ""),
            showarrow=False,
            font=dict(size=9, color="#444"),
            align="center",
        ))

        # Title
        annotations.append(dict(
            x=x_center, y=y1 - phase_band_height - 0.03,
            xref="paper", yref="paper",
            text=f"<b>{node.get('label','')}</b>",
            showarrow=False,
            font=dict(size=11, color="#222"),
            align="center"
        ))

        # Metrics text
        metrics = []
        if node.get("success_rate"): metrics.append(f"{node['success_rate']} success")
        if node.get("time_estimate"): metrics.append(node["time_estimate"])
        if node.get("volume_pct"): metrics.append(f"{node['volume_pct']}% volume")

        annotations.append(dict(
            x=x_center, y=y0+0.06,
            xref="paper", yref="paper",
            text=" · ".join(metrics),
            showarrow=False,
            font=dict(size=9, color="#777")
        ))

    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        margin=dict(l=30, r=30, t=20, b=20),
        font=dict(family="Helvetica, Arial, sans-serif"),
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
# STEP EDITOR
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
    c1, c2, c3 = st.columns(3)
    with c1:
        node["time_estimate"] = st.text_input("Time Estimate", node.get("time_estimate", ""))
    with c2:
        node["volume_pct"] = st.number_input("Volume %", value=float(node.get("volume_pct", 100)))
    with c3:
        node["success_rate"] = st.text_input("Success Rate (%)", str(node.get("success_rate", "")))

    st.markdown("### Ownership & Notes")
    node["owner"] = st.text_input("Owner", node.get("owner", ""))
    node["notes"] = st.text_area("Notes", node.get("notes", ""), height=80)

    st.markdown("### Links")
    links_text = "\n".join(node.get("links", []))
    updated_links = st.text_area("Links (one per line)", value=links_text)
    node["links"] = [l.strip() for l in updated_links.split("\n") if l.strip()]

    st.markdown("### Attachments")
    attachments = node.get("attachments", [])

    if attachments:
        st.caption("Existing files:")
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
# MAIN APP
# ------------------------------------------------------
def main():
    st.set_page_config(page_title="Global Launch Navigator", layout="wide", page_icon="🧭")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    st.title("🧭 Global Launch Navigator")
    st.caption("Editable launch flow with steps, metrics, attachments, and a premium-style Sankey flow.")

    # Sidebar – file management
    st.sidebar.header("Launch File")

    files = list_launch_files()
    if DEFAULT_FILE not in files:
        files.insert(0, DEFAULT_FILE)

    selected = st.sidebar.selectbox(
        "Select launch file",
        files,
        index=files.index(DEFAULT_FILE),
        format_func=lambda p: p.name
    )

    if "launch" not in st.session_state or st.session_state["file"] != str(selected):
        st.session_state["launch"] = load_launch(selected)
        st.session_state["file"] = str(selected)

    data = st.session_state["launch"]

    save_name = st.sidebar.text_input("Save As (filename.json)", value=selected.name)
    if st.sidebar.button("Save"):
        save_launch(data, DATA_DIR / save_name)
        st.sidebar.success(f"Saved as {save_name}")

    render_metrics(data)
    st.markdown("---")

    left, right = st.columns([2.2, 1.8])

    with left:
        st.subheader("Flow Overview")
        fig = build_sankey(data)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        render_node_editor(data)

    with st.expander("Show steps as table"):
        st.dataframe(pd.DataFrame(data["nodes"]))


if __name__ == "__main__":
    main()
