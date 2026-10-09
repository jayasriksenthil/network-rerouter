
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st

# Make the project root importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.network_engine.topology import (
    create_network,
    add_router,
    add_link,
    remove_link,
)

st.set_page_config(
    page_title="SentinelRoute",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ SentinelRoute")
st.subheader("Dynamic Network Topology Builder")
st.write(
    "Create your own network. Add routers, define connections, "
    "set link costs and capacities, and visualize the topology."
)

# Initialize one graph per browser session
if "network" not in st.session_state:
    st.session_state.network = create_network()

network = st.session_state.network

# ---------- ADD ROUTER ----------
st.header("1. Add a router")

with st.form("add_router_form", clear_on_submit=True):
    router_id = st.text_input(
        "Router ID",
        placeholder="For example, R1 or ServerA",
    ).strip()

    add_router_clicked = st.form_submit_button("Add router")

if add_router_clicked:
    try:
        add_router(network, router_id)
        st.success(f"Router '{router_id}' added!")
    except ValueError as error:
        st.error(str(error))

# Refresh router choices after any changes
routers = sorted(network.nodes)

st.divider()

# ---------- ADD LINK ----------
st.header("2. Connect two routers")

if len(routers) < 2:
    st.info("Add at least two routers before creating a link.")
else:
    with st.form("add_link_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            router_a = st.selectbox("First router", routers)

        with col2:
            router_b = st.selectbox(
                "Second router",
                routers,
                index=1,
            )

        col3, col4 = st.columns(2)

        with col3:
            cost = st.number_input(
                "Routing cost",
                min_value=0.1,
                value=1.0,
                step=0.5,
            )

        with col4:
            capacity = st.number_input(
                "Link capacity (Mbps)",
                min_value=0.1,
                value=100.0,
                step=10.0,
            )

        add_link_clicked = st.form_submit_button("Create link")

    if add_link_clicked:
        try:
            add_link(
                network,
                router_a,
                router_b,
                cost,
                capacity,
            )
            st.success(
                f"Link {router_a} ↔ {router_b} created!"
            )
        except ValueError as error:
            st.error(str(error))

st.divider()

# ---------- REMOVE LINK ----------
st.header("3. Remove a link")

edges = list(network.edges)

if edges:
    edge_options = {
        f"{a} ↔ {b}": (a, b)
        for a, b in edges
    }

    with st.form("remove_link_form"):
        selected_edge = st.selectbox(
            "Choose a connection",
            list(edge_options.keys()),
        )
        remove_link_clicked = st.form_submit_button(
            "Remove selected link"
        )

    if remove_link_clicked:
        a, b = edge_options[selected_edge]

        try:
            remove_link(network, a, b)
            st.success(f"Removed link {a} ↔ {b}.")
        except ValueError as error:
            st.error(str(error))
else:
    st.caption("There are no links to remove.")

st.divider()

# ---------- REMOVE ROUTER ----------
st.header("4. Remove a router")

routers = sorted(network.nodes)

if routers:
    with st.form("remove_router_form"):
        selected_router = st.selectbox(
            "Choose a router to remove",
            routers,
        )
        remove_router_clicked = st.form_submit_button(
            "Remove selected router"
        )

    if remove_router_clicked:
        network.remove_node(selected_router)
        st.success(
            f"Removed router {selected_router} and its connections."
        )
else:
    st.caption("There are no routers to remove.")

st.divider()

# ---------- NETWORK VISUALIZATION ----------
st.header("5. Network visualization")

col1, col2, col3 = st.columns(3)
col1.metric("Routers", network.number_of_nodes())
col2.metric("Links", network.number_of_edges())
col3.metric(
    "Connected components",
    nx.number_connected_components(network),
)

if network.number_of_nodes() == 0:
    st.info("Your network is empty. Add a router to begin.")
else:
    positions = nx.spring_layout(network, seed=42)

    fig, ax = plt.subplots(figsize=(10, 6))

    nx.draw_networkx(
        network,
        positions,
        ax=ax,
        node_color="#72B7B2",
        node_size=1800,
        font_size=10,
        font_weight="bold",
    )

    edge_labels = {
        (a, b): (
            f"Cost: {data['cost']}\n"
            f"Capacity: {data['capacity']} Mbps"
        )
        for a, b, data in network.edges(data=True)
    }

    nx.draw_networkx_edge_labels(
        network,
        positions,
        edge_labels=edge_labels,
        ax=ax,
        font_size=8,
    )

    ax.set_title("SentinelRoute Network")
    ax.axis("off")

    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Router inventory")
    st.write(routers)

    st.subheader("Link inventory")

    if network.number_of_edges() == 0:
        st.write("No connections created yet.")
    else:
        for a, b, data in network.edges(data=True):
            st.write(
                f"**{a} ↔ {b}** | "
                f"Cost: {data['cost']} | "
                f"Capacity: {data['capacity']} Mbps | "
                f"Status: {data.get('status', 'up')}"
            )
