
import json
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ATTACHMENTS_DIR = DATA_DIR / "attachments"
DATA_DIR.mkdir(exist_ok=True)
ATTACHMENTS_DIR.mkdir(exist_ok=True)

DEFAULT_FILE = DATA_DIR / "default_flow.json"

# Neutral, professional styling
CARD_CSS = """<style>
    .big-metric {
        font-size: 26px;
        font-weight: 700;
        margin-bottom: 0;
    }
    .big-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #888888;
        margin-top: -4px;
    }
    .stApp {
        background-color: #f5f5f7;
    }
</style>"""


PHASE_COLORS = {
    "Pilot & Initiate": "rgba(230, 236, 245, 0.9)",
    "Prepare & Startup": "rgba(230, 245, 240, 0.9)",
    "Execute & Adopt": "rgba(244, 234, 245, 0.9)",
    "Close & Sustain": "rgba(245, 240, 230, 0.9)",
}


def load_launch(file_path: Path) -> Dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_launch(data: Dict[str, Any], file_path: Path) -> None:
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_launch_files() -> List[Path]:
    return sorted([p for p in DATA_DIR.glob("*.json") if p.name != "example_backup.json"])


def build_sankey(launch: Dict[str, Any]):
    nodes = launch["nodes"]
    labels = [n["label"] for n in nodes]

    sources = []
    targets = []
    values = []
    link_colors = []

    for i in range(len(nodes) - 1):
        sources.append(i)
        targets.append(i + 1)
        values.append(nodes[i + 1].get("volume_pct", 100) or 100)
        link_colors.append("rgba(180, 180, 190, 0.5)")

    node_colors = [PHASE_COLORS.get(n["phase"], "rgba(255,255,255,1)") for n in nodes]

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=40,
                    thickness=28,
                    line=dict(color="rgba(0,0,0,0.05)", width=1),
                    label=labels,
                    color=node_colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=link_colors,
                ),
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(size=12, family="Helvetica, Arial, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_metrics(launch: Dict[str, Any]):
    nodes = launch["nodes"]
    total_steps = len(nodes)

    success_values = []
    for n in nodes:
        raw = str(n.get("success_rate", "")).strip().replace("%", "").replace(",", ".")
        try:
            val = float(raw)
            success_values.append(val)
        except ValueError:
            continue

    avg_success = round(sum(success_values) / len(success_values), 1) if success_values else None

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f'<p class="big-metric">{total_steps}</p>', unsafe_allow_html=True)
        st.markdown('<p class="big-label">Steps</p>', unsafe_allow_html=True)

    with col2:
        metric_text = f"{avg_success}%" if avg_success is not None else "—"
        st.markdown(f'<p class="big-metric">{metric_text}</p>', unsafe_allow_html=True)
        st.markdown('<p class="big-label">Avg. Success</p>', unsafe_allow_html=True)

    with col3:
        active = sum(1 for n in nodes if n.get("status") in ["In progress", "Planned"])
        st.markdown(f'<p class="big-metric">{active}</p>', unsafe_allow_html=True)
        st.markdown('<p class="big-label">Active Steps</p>', unsafe_allow_html=True)


def render_node_editor(launch: Dict[str, Any]):
    nodes = launch["nodes"]

    st.subheader("Step details")

    node_labels = [f"{n['id']}. {n['label']}" for n in nodes]
    node_index = st.selectbox("Select step", range(len(nodes)), format_func=lambda i: node_labels[i])

    node = nodes[node_index]

    st.markdown("##### Basic info")
    node["label"] = st.text_input("Title", value=node["label"])
    node["phase"] = st.selectbox(
        "Phase",
        ["Pilot & Initiate", "Prepare & Startup", "Execute & Adopt", "Close & Sustain"],
        index=["Pilot & Initiate", "Prepare & Startup", "Execute & Adopt", "Close & Sustain"].index(
            node.get("phase", "Pilot & Initiate")
        ),
    )
    node["description"] = st.text_area("Description", value=node.get("description", ""), height=100)

    st.markdown("##### Metrics")
    cols = st.columns(4)
    with cols[0]:
        node["time_estimate"] = st.text_input("Time estimate", value=node.get("time_estimate", ""))
    with cols[1]:
        node["volume_pct"] = st.number_input(
            "Volume %",
            min_value=0.0,
            max_value=100.0,
            value=float(node.get("volume_pct", 100.0)),
            step=1.0,
        )
    with cols[2]:
        node["success_rate"] = st.text_input("Success rate (%)", value=str(node.get("success_rate", "")))
    with cols[3]:
        node["status"] = st.selectbox(
            "Status",
            ["Planned", "In progress", "Blocked", "Completed"],
            index=["Planned", "In progress", "Blocked", "Completed"].index(
                node.get("status", "Planned")
            ),
        )

    st.markdown("##### Ownership & notes")
    cols2 = st.columns(2)
    with cols2[0]:
        node["owner"] = st.text_input("Owner / team", value=node.get("owner", ""))
    with cols2[1]:
        node["notes"] = st.text_area("Notes", value=node.get("notes", ""), height=80)

    st.markdown("##### Links")
    existing_links = node.get("links", [])
    links_text = "\n".join(existing_links)
    edited_links_text = st.text_area(
        "One link per line",
        value=links_text,
        height=80,
    )
    node["links"] = [ln.strip() for ln in edited_links_text.splitlines() if ln.strip()]

    st.markdown("##### Attachments")
    attachments = node.get("attachments", [])
    if attachments:
        st.caption("Existing attachments (relative paths):")
        for fn in attachments:
            st.write(f"- {fn}")

    uploaded_files = st.file_uploader(
        "Upload new attachment(s)", accept_multiple_files=True, key=f"upload_{node['id']}"
    )

    for up in uploaded_files:
        node_dir = ATTACHMENTS_DIR / f"launch_{launch['name'].replace(' ', '_')}" / f"step_{node['id']}"
        node_dir.mkdir(parents=True, exist_ok=True)
        file_path = node_dir / up.name
        with file_path.open("wb") as f:
            f.write(up.getbuffer())
        attachments.append(str(file_path.relative_to(BASE_DIR)))

    node["attachments"] = attachments


def main():
    st.set_page_config(
        page_title="Global Launch Navigator",
        layout="wide",
        page_icon="🧭",
    )
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    st.markdown("### Global Launch Navigator")
    st.caption("Interactive launch journey with editable steps, links and attachments.")

    st.sidebar.header("Launch selection")

    if not DEFAULT_FILE.exists():
        st.sidebar.error("default_flow.json not found in /data.")
        st.stop()

    files = list_launch_files()
    if DEFAULT_FILE not in files:
        files.insert(0, DEFAULT_FILE)

    selected_file = st.sidebar.selectbox(
        "Launch file",
        files,
        index=files.index(DEFAULT_FILE),
        format_func=lambda p: p.name,
    )

    if "launch_data" not in st.session_state or st.session_state.get("current_file") != str(selected_file):
        st.session_state.launch_data = load_launch(selected_file)
        st.session_state.current_file = str(selected_file)

    launch = st.session_state.launch_data

    st.sidebar.text_input("Launch name", value=launch.get("name", ""), key="launch_name_sidebar")
    launch["name"] = st.session_state.launch_name_sidebar

    st.sidebar.text_area(
        "Short description",
        value=launch.get("description", ""),
        key="launch_desc_sidebar",
        height=80,
    )
    launch["description"] = st.session_state.launch_desc_sidebar

    new_filename = st.sidebar.text_input(
        "Save as (optional, e.g. wave1_launch.json)",
        value=Path(selected_file).name,
    )

    if st.sidebar.button("Save launch file"):
        target_path = DATA_DIR / new_filename
        save_launch(launch, target_path)
        st.sidebar.success(f"Saved to {target_path.name}")

    st.sidebar.markdown("---")
    st.sidebar.caption("Files are stored under `/data`. Commit them to version-control when needed.")

    render_metrics(launch)

    st.markdown("")
    col_chart, col_editor = st.columns([2, 1.4])

    with col_chart:
        st.markdown("#### Flow overview")
        fig = build_sankey(launch)
        st.plotly_chart(fig, use_container_width=True)

    with col_editor:
        render_node_editor(launch)

    with st.expander("See all steps as a table"):
        df = pd.DataFrame(launch["nodes"])
        cols_to_show = ["id", "label", "phase", "status", "owner", "time_estimate", "success_rate", "volume_pct"]
        st.dataframe(df[cols_to_show])


if __name__ == "__main__":
    main()
