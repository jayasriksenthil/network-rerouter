
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st

# Make the project root importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.network_engine.storage import (
    init_db,
    save_network,
    list_saved_networks,
    load_network,
)
from backend.network_engine.routing import find_best_route
init_db()
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



st.header("Save or load a network")

save_col, load_col = st.columns(2)

with save_col:
    with st.form("save_network_form"):
        network_name = st.text_input(
            "Network name",
            placeholder="e.g. CampusNetwork"
        )
        save_clicked = st.form_submit_button("Save network")

    if save_clicked:
        try:
            save_network(
                network_name,
                st.session_state.network
            )
            st.success(
                f"Network '{network_name.strip()}' saved!"
            )
        except (ValueError, TypeError) as error:
            st.error(str(error))


with load_col:
    saved_names = list_saved_networks()

    if saved_names:
        with st.form("load_network_form"):
            selected_name = st.selectbox(
                "Choose a saved network",
                saved_names,
                key="saved_network_choice",
            )
            load_clicked = st.form_submit_button("Load network")

        
    if load_clicked:
        try:
            loaded_network = load_network(selected_name)

            # Show what was actually retrieved from SQLite
            st.write("DEBUG — Loaded network:", selected_name)
            st.write("DEBUG — Routers:", list(loaded_network.nodes))
            st.write("DEBUG — Links:", list(loaded_network.edges(data=True)))

            # Replace the current graph
            st.session_state.network = loaded_network

            # Clear the old route result
            st.session_state.pop("route_result", None)
            st.session_state.pop("route_request", None)

            st.success(
                f"Loaded '{selected_name}': "
                f"{loaded_network.number_of_nodes()} routers and "
                f"{loaded_network.number_of_edges()} links."
            )

        except Exception as error:
            st.error(f"Loading failed: {type(error).__name__}: {error}")


        except (ValueError, TypeError, KeyError) as error:
            st.error(f"Could not load network: {error}")
    else:
        st.info("No saved networks yet. Create and save one first.")



network = st.session_state.network

# ADD ROUTER 
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

# ADD LINK 
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

# REMOVE LINK 
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

#  REMOVE ROUTER 
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

# ROUTE FINDER
st.divider()
st.header("6. Find the best route")
st.write(
    "Choose a source and destination to find the "
    "lowest-cost route using working links."
)

routers = sorted(network.nodes)

if len(routers) < 2:
    st.info("Add at least two routers to find a route.")
else:
    with st.form("find_route_form"):
        col1, col2 = st.columns(2)

        with col1:
            source = st.selectbox(
                "Source router",
                routers,
                key="route_source",
            )

        with col2:
            destination = st.selectbox(
                "Destination router",
                routers,
                index=1,
                key="route_destination",
            )

        find_route_clicked = st.form_submit_button(
            "Find Best Route"
        )

    if find_route_clicked:
        result = find_best_route(
            network,
            source,
            destination,
        )

        st.session_state.route_result = result
        st.session_state.route_request = (
            source,
            destination,
        )

    # Display the most recent route result
    if "route_result" in st.session_state:
        result = st.session_state.route_result
        route_source, route_destination = (
            st.session_state.route_request
        )

        st.subheader(
            f"Route: {route_source} → {route_destination}"
        )

        if result["status"] == "success":
            st.success(result["message"])

            st.metric(
                "Total routing cost",
                result["total_cost"],
            )

            st.write("**Selected path**")
            st.code(" → ".join(result["path"]))

        elif result["status"] == "unreachable":
            st.warning(result["message"])

        else:
            st.error(result["message"])

#  NETWORK VISUALIZATION 
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

    # Retrieve the latest route result, if one exists
    result = st.session_state.get("route_result", {})
    route = result.get("path", [])
    route_edges = {
        frozenset((route[i], route[i + 1]))
        for i in range(len(route) - 1)
    } if result.get("status") == "success" else set()

    # Separate selected-route links from the other links
    normal_edges = [
        (a, b)
        for a, b in network.edges()
        if frozenset((a, b)) not in route_edges
    ]

    selected_edges = [
        (a, b)
        for a, b in network.edges()
        if frozenset((a, b)) in route_edges
    ]

    nx.draw_networkx_nodes(
        network, positions, ax=ax,
        node_color="#72B7B2", node_size=1800
    )

    nx.draw_networkx_labels(
        network, positions, ax=ax,
        font_size=10, font_weight="bold"
    )

    # Draw ordinary links in grey
    nx.draw_networkx_edges(
        network, positions, ax=ax,
        edgelist=normal_edges,
        edge_color="gray", width=1.8
    )

    # Highlight the chosen route in green
    nx.draw_networkx_edges(
        network, positions, ax=ax,
        edgelist=selected_edges,
        edge_color="green", width=4
    )

    edge_labels = {
        (a, b): (
            f"Cost: {data['cost']}\n"
            f"Capacity: {data['capacity']} Mbps"
        )
        for a, b, data in network.edges(data=True)
    }

    nx.draw_networkx_edge_labels(
        network, positions, edge_labels=edge_labels,
        ax=ax, font_size=8
    )

    ax.set_title("SentinelRoute Network — Selected Route in Green")
    ax.axis("off")
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Router inventory")
    st.write(sorted(network.nodes))

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
