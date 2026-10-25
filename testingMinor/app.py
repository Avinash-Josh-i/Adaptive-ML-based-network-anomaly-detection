import streamlit as st
import pandas as pd
import time
import os
import subprocess
import psutil
import altair as alt

st.set_page_config(page_title="IDS Monitoring", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stAppDeployButton"] { display: none; }
    [data-testid="stStatusWidget"] { display: none; }
    </style>
""",
    unsafe_allow_html=True,
)
MAIN_EXE = (
    r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\main.exe"
)
BIN_DIR = r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin"
STATS_CSV = (
    r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\stats.csv"
)
STATS_HISTORY_CSV = r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\stats_history.csv"
ANOMALY_LOG_CSV = r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\anomaly_log.csv"
FLOW_CSV = (
    r"..\adaptive_ml_based_network_anamoly_detection\feature_extract\bin\flows.csv"
)
PREDICTION_CSV = "prediction_output.csv"

SPINNERS = ["◐", "◓", "◑", "◒"]


@st.cache_data(show_spinner=False)
def get_interfaces():
    time.sleep(5)
    result = subprocess.run(
        [MAIN_EXE, "--list"], cwd=BIN_DIR, capture_output=True, text=True
    )
    interfaces = {}
    for line in result.stdout.splitlines():
        if line and line[0].isdigit() and ": " in line:
            iface_index, interface = line.split(": ", 1)
            if "|" in interface:
                iface_name = interface.split("|", 1)[1].strip()
            else:
                iface_name = interface.strip()
            interfaces[iface_name] = int(iface_index.strip())
    return interfaces


@st.cache_data(ttl=1)
def load_stats():
    if os.path.exists(STATS_CSV):
        return pd.read_csv(STATS_CSV).iloc[0]
    return None


def load_stats_history():
    if os.path.exists(STATS_HISTORY_CSV):
        return pd.read_csv(STATS_HISTORY_CSV).to_dict("records")
    return []


def load_anomaly_history():
    if os.path.exists(ANOMALY_LOG_CSV):
        anomaly_log = pd.read_csv(ANOMALY_LOG_CSV).to_dict("records")
        st.session_state.anomaly_count = len(anomaly_log)
        return anomaly_log
    else:
        return None


def load_data():
    if os.path.exists(PREDICTION_CSV):
        return pd.read_csv(PREDICTION_CSV)
    return None


def reset_all():
    st.session_state.anomaly_log = []
    st.session_state.stats_history = []
    st.session_state.loading_number = 0
    st.session_state.anomaly_count = 0
    st.session_state.last_anomaly_session = 0
    st.session_state.stats = None
    st.session_state.predicted_df = None
    if os.path.exists(STATS_CSV):
        os.remove(STATS_CSV)
    if os.path.exists(STATS_HISTORY_CSV):
        os.remove(STATS_HISTORY_CSV)
    if os.path.exists(PREDICTION_CSV):
        os.remove(PREDICTION_CSV)
    if os.path.exists(FLOW_CSV):
        os.remove(FLOW_CSV)
    if os.path.exists(ANOMALY_LOG_CSV):
        os.remove(ANOMALY_LOG_CSV)
    st.session_state.show_toast = "Data History Cleared!"


def start_capture():
    st.session_state.stats_history = []
    if os.path.exists(STATS_HISTORY_CSV):
        os.remove(STATS_HISTORY_CSV)
        time.sleep(0.2)
    subprocess.Popen(
        [
            MAIN_EXE,
            "--iface",
            str(st.session_state.get("iface_index")),
            "--seconds",
            str(st.session_state.get("capture_seconds")),
            "--label",
            str(st.session_state.get("label")),
        ],
        cwd=BIN_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    st.session_state.is_capturing = True
    st.session_state.show_toast = "Capture Started!"


def loading_area(loading_msg):
    with graph_area.container():
        st.markdown(
            f"""
                <div style='text-align:center; padding:80px; font-size:24px; color:#4FC3F7'>
                    {loading_msg} {SPINNERS[st.session_state.loading_number % len(SPINNERS)]}
                </div>
                """,
            unsafe_allow_html=True,
        )
        st.session_state.loading_number += 1


def stats_detail():
    with header_area.container():
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        st.session_state.remaining = int(st.session_state.stats["total"]) - int(
            st.session_state.stats["elapsed"]
        )
        if st.session_state.remaining < 0:
            st.session_state.remaining == 0
        m1.metric("Session Packets Captured", int(st.session_state.stats["raw"]))
        m2.metric("Session Flows", int(st.session_state.stats["flows"]))
        m3.metric("Total Flows", int(st.session_state.stats["total_flows"]))
        m4.metric(
            "Current Threshold",
            (
                f"{st.session_state.predicted_df['ThresholdUsed'].iloc[0]:.5f}"
                if os.path.exists(PREDICTION_CSV)
                else "N/A"
            ),
        )
        m5.metric("Anomaly Count", st.session_state.anomaly_count)

        if (
            st.session_state.remaining == 0
            and st.session_state.prev_remaining > 0
            and st.session_state.get("is_capturing")
        ):
            st.session_state.is_capturing = False
            st.session_state.prev_remaining = 0
        else:
            st.session_state.prev_remaining = st.session_state.remaining
        threshold_value = (
            st.session_state.predicted_df["ThresholdUsed"].iloc[0]
            if os.path.exists(PREDICTION_CSV)
            else 0
        )
        if st.session_state.remaining == 0:
            info_area.success("✅ Flow Capture Completed!")
            m6.metric("Session Number", int(st.session_state.stats["session"]))
            if not st.session_state.get("get_final_stats"):
                st.session_state.stats_history.append(
                    {
                        "Time": int(st.session_state.stats["elapsed"]),
                        "Packets": int(st.session_state.stats["raw"]),
                        "Flows": int(st.session_state.stats["flows"]),
                        "Threshold": threshold_value,
                    }
                )
                st.session_state.get_final_stats = True

        else:
            st.session_state.get_final_stats = False
            st.session_state.stats_history.append(
                {
                    "Time": int(st.session_state.stats["elapsed"]),
                    "Packets": int(st.session_state.stats["raw"]),
                    "Flows": int(st.session_state.stats["flows"]),
                    "Threshold": threshold_value,
                }
            )
            st.session_state.is_capturing = True
            progress = st.session_state.remaining / int(st.session_state.stats["total"])
            info_area.progress(
                1 - progress,
                text=f"Capturing... {(1 - progress) * 100:.2f}% done!",
            )
            m6.metric("Time Remaining", f"{st.session_state.remaining}s")


def stats_graph():
    with graph_area.container():
        stats_df = pd.DataFrame(st.session_state.stats_history)
        pd.DataFrame(st.session_state.stats_history).to_csv(
            os.path.join(BIN_DIR, "stats_history.csv"), index=False
        )
        c1, c2, c3 = st.columns(3)
        packets_axes = (
            alt.Chart(stats_df)
            .mark_line(interpolate="monotone", color="#A29BFE")
            .encode(
                x=alt.X("Time:Q", title="Time(s)"),
                y=alt.Y("Packets:Q", title="Packets Captured"),
            )
            .properties(height=400, title="Packets Captured")
        )
        threshold_axes = (
            alt.Chart(stats_df)
            .mark_line(interpolate="monotone", color="#FDCB6E")
            .encode(
                x=alt.X("Time:Q", title="Time(s)"),
                y=alt.Y("Threshold:Q", title="Threshold"),
            )
            .properties(height=400, title="Live Threshold")
            .interactive()
        )
        flows_axes = (
            alt.Chart(stats_df)
            .mark_line(interpolate="monotone", color="#4FC3F7")
            .encode(
                x=alt.X("Time:Q", title="Time(s)"),
                y=alt.Y("Flows:Q", title="Flows"),
            )
            .properties(height=400, title="Flows Detected")
        )

        with c1:
            st.altair_chart(packets_axes, width="stretch")
        with c2:
            st.altair_chart(flows_axes, width="stretch")
        with c3:
            st.altair_chart(threshold_axes, width="stretch")


def predicted_graph():
    with graph_area_plot.container():
        st.session_state.plot_df = pd.DataFrame(
            {
                "Anomaly Score": st.session_state.predicted_df["AnomalyScore"],
                "Threshold": st.session_state.predicted_df["ThresholdUsed"],
            }
        )
        st.session_state.plot_df["index"] = range(1, len(st.session_state.plot_df) + 1)
        st.session_state.plot_df["Status"] = st.session_state.plot_df.apply(
            lambda row: (
                "Anomaly" if row["Anomaly Score"] >= row["Threshold"] else "Normal"
            ),
            axis=1,
        )
        st.session_state.plot_df["ThresholdLabel"] = "Threshold"
        base_axes = alt.Chart(st.session_state.plot_df).encode(
            x=alt.X(
                "index:Q",
                title="Flows",
                scale=alt.Scale(domain=[0, len(st.session_state.plot_df) + 1]),
                axis=alt.Axis(tickMinStep=1),
            )
        )

        score_points = base_axes.mark_point(
            size=50,
            filled=True,
        ).encode(
            y=alt.Y(
                "Anomaly Score:Q",
                title="Anomaly Score",
                scale=alt.Scale(domainMin=-0.01),
            ),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(
                    domain=["Normal", "Anomaly"], range=["#00B894", "#FF4444"]
                ),
            ),
        )

        threshold_line = base_axes.mark_line(size=2).encode(
            y=alt.Y("Threshold:Q"),
            color=alt.Color(
                "ThresholdLabel:N",
                scale=alt.Scale(domain=["Threshold"], range=["#FDCB6E"]),
                legend=alt.Legend(title=None),
            ),
        )

        predicted_axes = (
            alt.layer(score_points, threshold_line)
            .resolve_scale(color="independent")
            .properties(height=500)
            .interactive()
        )

        st.altair_chart(predicted_axes, width="stretch")


def anomaly_counter():
    if (
        st.session_state.predicted_df["AnomalyScore"]
        >= st.session_state.predicted_df["ThresholdUsed"]
    ).any():
        st.session_state.anomaly_log = []
        st.session_state.anomaly_count = 0
        anomalies = st.session_state.predicted_df[
            st.session_state.predicted_df["AnomalyScore"]
            >= st.session_state.predicted_df["ThresholdUsed"]
        ]
        for _, row in anomalies.iterrows():
            st.session_state.anomaly_count += 1
            st.session_state.anomaly_log.insert(
                0,
                {
                    "Time": time.strftime("%H:%M:%S"),
                    "Score": round(row["AnomalyScore"], 6),
                    "Threshold": round(row["ThresholdUsed"], 6),
                    "Source IP": f"{row['SrcIP']}:{row['SrcPort']}",
                    "Destination IP": f"{row['DstIP']}:{row['DstPort']}",
                    "Protocol": "TCP" if row["Protocol"] == 6 else "UDP",
                },
            )
            pd.DataFrame(st.session_state.anomaly_log).to_csv(
                os.path.join(BIN_DIR, "anomaly_log.csv"), index=False
            )
    if st.session_state.anomaly_count > 0:
        status_area.error("🚨 Anomalies Detected!")
    else:
        status_area.success("✅ Network Clear! No anomalies detected.")


def show_table():
    with table_area.container():
        st.subheader("🚨 Anomaly Identification Table")
        anomaly_df = pd.DataFrame(st.session_state.anomaly_log)
        anomaly_df.index = range(1, len(anomaly_df) + 1)
        anomaly_df.index.name = "S.N."
        if len(anomaly_df) > 0:
            st.dataframe(anomaly_df)
            st.caption(f"Showing {len(anomaly_df)} suspicious flows.")
        else:
            st.info("No anomaly logged yet. Network is clear.")


@st.fragment(run_every=1)
def sidebar_settings():
    current_ifaces = set(psutil.net_if_addrs().keys())
    if (
        current_ifaces != st.session_state.get("last_psutil_ifaces")
        or st.session_state.get_interfaces is None
    ):
        st.session_state.last_psutil_ifaces = current_ifaces
        get_interfaces.clear()
        st.session_state.get_interfaces = get_interfaces()
    st.header("⚙️ Settings")
    st.slider("Capture Duration (seconds)", 10, 300, 60, key="capture_seconds")
    st.selectbox("Label", [0, 1], key="label")
    if st.session_state.get_interfaces is None:
        st.selectbox("Network Interface", "No Interface Detected")
    else:
        iface = st.selectbox(
            "Network Interface", list(st.session_state.get_interfaces.keys())
        )
        st.session_state.iface_index = st.session_state.get_interfaces[iface]
    st.button(
        "▶ Start Flow Capture",
        disabled=st.session_state.is_capturing,
        on_click=start_capture,
    )
    st.checkbox("Show Graph", value=True, key="graph_key")
    st.checkbox("Show Security Log", value=False, key="log_key")
    st.button(
        "Clear All Data",
        key="reset_btn",
        on_click=reset_all,
        disabled=st.session_state.is_capturing,
    )


@st.fragment(run_every=1)
def main_window():
    st.session_state.predicted_df = load_data()
    show_graph = st.session_state.get("graph_key", True)
    show_log = st.session_state.get("log_key", False)
    if st.session_state.get("show_toast"):
        st.toast(st.session_state.show_toast, icon="✅")
        st.session_state.show_toast = None

    st.session_state.stats = load_stats()

    if st.session_state.stats is None:
        with header_area.container():
            st.info("📡 Scanning Network... Gathering initial traffic.")
        loading_area("Scanning for First Flow")
        info_area.empty()
        status_area.empty()
        graph_area_plot.empty()
    else:
        stats_detail()
        if not show_graph:
            graph_area.empty()
        elif show_graph:
            stats_graph()
            if os.path.exists(PREDICTION_CSV):
                anomaly_counter()
                predicted_graph()
        else:
            loading_area("Waiting for Prediction to Complete")
            status_area.empty()

    if show_log:
        show_table()
    else:
        table_area.empty()


if "get_interfaces" not in st.session_state:
    st.session_state.get_interfaces = None
if "iface_index" not in st.session_state:
    st.session_state.iface_index = ""
if "last_psutil_ifaces" not in st.session_state:
    st.session_state.last_psutil_ifaces = set(psutil.net_if_addrs().keys())
if "loading_number" not in st.session_state:
    st.session_state.loading_number = 0
if "stats" not in st.session_state:
    st.session_state.stats = None
if "is_capturing" not in st.session_state:
    st.session_state.is_capturing = False
if "show_toast" not in st.session_state:
    st.session_state.show_toast = None
if "prev_remaining" not in st.session_state:
    st.session_state.prev_remaining = 0
if "remaining" not in st.session_state:
    st.session_state.remaining = 0
if "predicted_df" not in st.session_state:
    st.session_state.predicted_df = None
if "plot_df" not in st.session_state:
    st.session_state.plot_df = []
if "anomaly_count" not in st.session_state:
    st.session_state.anomaly_count = 0
if "anomaly_log" not in st.session_state:
    st.session_state.anomaly_log = load_anomaly_history()
if "stats_history" not in st.session_state:
    st.session_state.stats_history = load_stats_history()
if "get_final_stats" not in st.session_state:
    st.session_state.get_final_stats = False

placeholder = st.empty()
with st.sidebar:
    sidebar_settings()

title_area = st.empty()
header_area = st.empty()
info_area = st.empty()
graph_area = st.empty()
graph_area_plot = st.empty()
status_area = st.empty()
table_area = st.empty()

title_area.title("🛡️ IDS Adaptive Threshold Monitoring")

main_window()
