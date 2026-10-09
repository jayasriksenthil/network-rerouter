
import sys
from pathlib import Path

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------
# IMPORT PROJECT MODULES
# --------------------------------------------------
from backend.network_engine.topology import (
    create_network,
    add_router,
    add_link,
    remove_link,
)

from backend.network_engine.routing import find_best_route

from backend.network_engine.storage import (
    init_db,
    save_network,
    list_saved_networks,
    load_network,
)

from Failure_Recovery.failure_recovery import (
    fail_link,
    restore_link,
    get_failed_links,
    check_link_status,
    calculate_resilience,
    compare_failure_scenario,
    detect_security_scenarios,
    recover_route,
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="SentinelRoute",
    page_icon="🌐",
    layout="wide",
)

init_db()

if "network" not in st.session_state:
    st.session_state.network = create_network()

network = st.session_state.network

st.title("🌐 SentinelRoute")
st.subheader("The Internet Goes Down — Network Rerouter")

st.write(
    "Create network topologies, find the best routes, "
    "simulate link failures, and analyze network resilience."
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("Network Overview")

st.sidebar.metric("Routers", network.number_of_nodes())
st.sidebar.metric("Links", network.number_of_edges())
st.sidebar.metric("Failed Links", len(get_failed_links(network)))

st.sidebar.divider()
st.sidebar.subheader("Save Network")

network_name = st.sidebar.text_input(
    "Enter network name"
)

if st.sidebar.button("Save Network"):
    try:
        save_network(network_name, network)
        st.sidebar.success("Network saved successfully.")
    except ValueError as error:
        st.sidebar.error(str(error))

saved_networks = list_saved_networks()

if saved_networks:
    selected_network = st.sidebar.selectbox(
        "Saved networks",
        saved_networks,
    )

    if st.sidebar.button("Load Network"):
        try:
            st.session_state.network = load_network(selected_network)
            st.rerun()
        except ValueError as error:
            st.sidebar.error(str(error))

if st.sidebar.button("Reset Network"):
    st.session_state.network = create_network()
    st.rerun()

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Topology",
        "Routing",
        "Failure Recovery",
        "Resilience",
        "Security",
    ]
)

# ==================================================
# TAB 1: TOPOLOGY
# ==================================================
with tab1:
    st.header("Network Topology")

    col1, col2 = st.columns(2)

    # Add router
    with col1:
        st.subheader("Add Router")

        with st.form("router_form"):
            router_id = st.text_input("Router ID")
            add_router_button = st.form_submit_button("Add Router")

        if add_router_button:
            try:
                add_router(network, router_id)
                st.success(f"Router {router_id.strip()} added.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    # Add link
    with col2:
        st.subheader("Add Link")

        routers = list(network.nodes)

        if len(routers) >= 2:
            with st.form("link_form"):
                router_a = st.selectbox(
                    "Router A",
                    routers,
                    key="router_a",
                )

                router_b = st.selectbox(
                    "Router B",
                    routers,
                    index=1,
                    key="router_b",
                )

                cost = st.number_input(
                    "Link Cost",
                    min_value=0.1,
                    value=1.0,
                )

                capacity = st.number_input(
                    "Capacity (Mbps)",
                    min_value=0.1,
                    value=100.0,
                )

                add_link_button = st.form_submit_button("Add Link")

            if add_link_button:
                try:
                    add_link(
                        network,
                        router_a,
                        router_b,
                        cost,
                        capacity,
                    )
                    st.success(
                        f"Link {router_a} - {router_b} added."
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        else:
            st.info("Add at least two routers first.")

    st.divider()

    st.subheader("Current Routers")
    st.write(list(network.nodes))

    st.subheader("Current Links")

    link_rows = []

    for a, b, data in network.edges(data=True):
        link_rows.append(
            {
                "Router A": a,
                "Router B": b,
                "Cost": data.get("cost"),
                "Capacity": data.get("capacity"),
                "Status": data.get("status", "up"),
            }
        )

    if link_rows:
        st.dataframe(link_rows, use_container_width=True)
    else:
        st.info("No links created yet.")

    # Remove link
    edges = list(network.edges)

    if edges:
        st.subheader("Remove Link")

        selected_edge = st.selectbox(
            "Select link to remove",
            edges,
            format_func=lambda edge: f"{edge[0]} - {edge[1]}",
        )

        if st.button("Remove Selected Link"):
            try:
                remove_link(network, *selected_edge)
                st.success("Link removed.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

# ==================================================
# TAB 2: ROUTING
# ==================================================
with tab2:
    st.header("Find Best Route")

    routers = list(network.nodes)

    if routers:
        col1, col2 = st.columns(2)

        with col1:
            source = st.selectbox(
                "Source Router",
                routers,
                key="source_router",
            )

        with col2:
            destination = st.selectbox(
                "Destination Router",
                routers,
                index=min(1, len(routers) - 1),
                key="destination_router",
            )

        if st.button("Find Route"):
            result = find_best_route(
                network,
                source,
                destination,
            )

            if result["status"] == "success":
                st.success(result["message"])
                st.write(
                    "**Path:** "
                    + " → ".join(map(str, result["path"]))
                )
                st.metric("Total Cost", result["total_cost"])

            elif result["status"] == "unreachable":
                st.error(result["message"])

            else:
                st.error(result["message"])
    else:
        st.info("Add routers to find routes.")

# ==================================================
# TAB 3: FAILURE RECOVERY
# ==================================================
with tab3:
    st.header("Failure Recovery")

    edges = list(network.edges)

    if edges:
        selected_edge = st.selectbox(
            "Select link",
            edges,
            format_func=lambda edge: f"{edge[0]} - {edge[1]}",
            key="failure_link",
        )

        a, b = selected_edge

        status = check_link_status(network, a, b)

        st.write(f"Link status: **{status['status'].upper()}**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Simulate Failure"):
                try:
                    result = fail_link(network, a, b)
                    st.warning(result["message"])
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        with col2:
            if st.button("Restore Link"):
                try:
                    result = restore_link(network, a, b)
                    st.success(result["message"])
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        st.divider()
        st.subheader("Recover Route")

        routers = list(network.nodes)

        if routers:
            recovery_source = st.selectbox(
                "Recovery Source",
                routers,
                key="recovery_source",
            )

            recovery_destination = st.selectbox(
                "Recovery Destination",
                routers,
                index=min(1, len(routers) - 1),
                key="recovery_destination",
            )

            if st.button("Recover Route"):
                result = recover_route(
                    network,
                    recovery_source,
                    recovery_destination,
                )

                if result["recovered"]:
                    st.success(result["message"])
                    st.write(
                        "**Path:** "
                        + " → ".join(map(str, result["path"]))
                    )
                    st.write(f"**Cost:** {result['total_cost']}")
                else:
                    st.error(result["message"])

    else:
        st.info("Add links before simulating failures.")

    st.subheader("Failed Links")

    failed_links = get_failed_links(network)

    if failed_links:
        for a, b in failed_links:
            st.error(f"{a} - {b} is DOWN")
    else:
        st.success("No failed links.")

# ==================================================
# TAB 4: RESILIENCE
# ==================================================
with tab4:
    st.header("Network Resilience Analysis")

    routers = list(network.nodes)

    if len(routers) >= 2:
        source = st.selectbox(
            "Analysis Source",
            routers,
            key="resilience_source",
        )

        destinations = st.multiselect(
            "Destinations",
            [router for router in routers if router != source],
            default=[router for router in routers if router != source],
        )

        if st.button("Calculate Resilience"):
            result = calculate_resilience(
                network,
                source,
                destinations,
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "Reachable",
                f"{result['reachable_count']} / "
                f"{result['total_destinations']}",
            )

            col2.metric(
                "Reachability",
                f"{result['reachability_percent']}%",
            )

            if result["unreachable_destinations"]:
                st.warning(
                    "Unreachable: "
                    + ", ".join(
                        map(str, result["unreachable_destinations"])
                    )
                )
            else:
                st.success("All selected destinations are reachable.")

        st.divider()
        st.subheader("Test Hypothetical Failures")

        edges = list(network.edges)

        if edges:
            failed_scenario = st.multiselect(
                "Links to fail in simulation",
                edges,
                format_func=lambda edge: f"{edge[0]} - {edge[1]}",
                key="hypothetical_failures",
            )

            if st.button("Run Scenario"):
                try:
                    result = compare_failure_scenario(
                        network,
                        source,
                        destinations,
                        failed_scenario,
                    )

                    resilience = result["resilience"]

                    st.metric(
                        "Reachability After Failure",
                        f"{resilience['reachability_percent']}%",
                    )

                    st.write(
                        f"Reachable destinations: "
                        f"{resilience['reachable_count']} / "
                        f"{resilience['total_destinations']}"
                    )

                    if resilience["unreachable_destinations"]:
                        st.warning(
                            "Unreachable: "
                            + ", ".join(
                                map(
                                    str,
                                    resilience["unreachable_destinations"],
                                )
                            )
                        )

                    st.caption(
                        "This is a simulation; the original network "
                        "is not modified."
                    )

                except ValueError as error:
                    st.error(str(error))
    else:
        st.info("Add at least two routers for resilience analysis.")

# ==================================================
# TAB 5: SECURITY
# ==================================================
with tab5:
    st.header("Security Scenario Checks")

    threshold = st.slider(
        "Utilization Alert Threshold (%)",
        min_value=1,
        max_value=100,
        value=80,
    )

    routers = list(network.nodes)

    if routers:
        router_to_flag = st.selectbox(
            "Select router",
            routers,
            key="security_router",
        )

        suspicious = network.nodes[router_to_flag].get(
            "suspicious", False
        )

        if st.button(
            "Unmark Router" if suspicious else "Mark Suspicious"
        ):
            network.nodes[router_to_flag]["suspicious"] = not suspicious
            st.rerun()

    edges = list(network.edges)

    if edges:
        selected_util_edge = st.selectbox(
            "Link for utilization data",
            edges,
            format_func=lambda edge: f"{edge[0]} - {edge[1]}",
            key="security_link",
        )

        a, b = selected_util_edge
        data = network[a][b]

        utilization = st.number_input(
            "Utilization (Mbps)",
            min_value=0.0,
            value=float(data.get("utilization_mbps", 0.0)),
            key="utilization_input",
        )

        capacity = st.number_input(
            "Capacity (Mbps)",
            min_value=0.1,
            value=max(0.1, float(data.get("capacity", 100.0))),
            key="security_capacity",
        )

        if st.button("Save Utilization"):
            data["utilization_mbps"] = utilization
            data["capacity"] = capacity
            st.success("Utilization saved.")

    if st.button("Run Security Checks"):
        result = detect_security_scenarios(
            network,
            utilization_threshold=threshold,
        )

        st.subheader("Suspicious Routers")

        if result["suspicious_nodes"]:
            for router in result["suspicious_nodes"]:
                st.warning(f"Router flagged: {router}")
        else:
            st.success("No routers marked suspicious.")

        st.subheader("High-Utilization Links")

        if result["high_utilization_links"]:
            rows = []

            for item in result["high_utilization_links"]:
                rows.append(
                    {
                        "Link": (
                            f"{item['link'][0]} - {item['link'][1]}"
                        ),
                        "Utilization (Mbps)": item["utilization_mbps"],
                        "Capacity (Mbps)": item["capacity_mbps"],
                        "Utilization (%)": item["utilization_percent"],
                        "Status": item["status"],
                    }
                )

            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No high-utilization links detected.")

        st.caption(result["note"])

# ==================================================
# NETWORK GRAPH
# ==================================================
st.divider()
st.header("Network Visualization")

if network.number_of_nodes() == 0:
    st.info("Add routers to display the graph.")

else:
    fig, ax = plt.subplots(figsize=(11, 6))

    positions = nx.spring_layout(network, seed=42)

    failed_edges = get_failed_links(network)

    failed_set = {
        frozenset(edge)
        for edge in failed_edges
    }

    active_edges = [
        (a, b)
        for a, b in network.edges
        if frozenset((a, b)) not in failed_set
    ]

    nx.draw_networkx_nodes(
        network,
        positions,
        node_color="lightblue",
        node_size=1400,
        ax=ax,
    )

    nx.draw_networkx_labels(
        network,
        positions,
        font_weight="bold",
        ax=ax,
    )

    nx.draw_networkx_edges(
        network,
        positions,
        edgelist=active_edges,
        edge_color="gray",
        width=2,
        ax=ax,
    )

    if failed_edges:
        nx.draw_networkx_edges(
            network,
            positions,
            edgelist=failed_edges,
            edge_color="red",
            style="dashed",
            width=2.5,
            ax=ax,
        )

    edge_labels = {
        (a, b): (
            f"Cost: {data.get('cost', '?')}\n"
            f"{data.get('status', 'up').upper()}"
        )
        for a, b, data in network.edges(data=True)
    }

    nx.draw_networkx_edge_labels(
        network,
        positions,
        edge_labels=edge_labels,
        font_size=8,
        ax=ax,
    )

    ax.set_axis_off()
    fig.tight_layout()

    st.pyplot(fig)
    plt.close(fig)

    st.caption(
        "Gray lines = operational links. "
        "Red dashed lines = failed links."
    )

st.caption("SentinelRoute | Network Rerouter")
