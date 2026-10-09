from copy import deepcopy

import networkx as nx


def fail_link(network, node_a, node_b):
    """Mark a link as failed without deleting it from the topology."""
    if not network.has_edge(node_a, node_b):
        raise ValueError(f"Link {node_a}-{node_b} does not exist.")

    network[node_a][node_b]["status"] = "down"
    return {
        "link": (node_a, node_b),
        "status": "down",
        "message": f"Link {node_a}-{node_b} has failed.",
    }


def restore_link(network, node_a, node_b):
    """Restore a failed link to operational status."""
    if not network.has_edge(node_a, node_b):
        raise ValueError(f"Link {node_a}-{node_b} does not exist.")

    network[node_a][node_b]["status"] = "up"
    return {
        "link": (node_a, node_b),
        "status": "up",
        "message": f"Link {node_a}-{node_b} has been restored.",
    }


def get_failed_links(network):
    """Return all links whose status is down."""
    return [
        (node_a, node_b)
        for node_a, node_b, data in network.edges(data=True)
        if data.get("status", "up") == "down"
    ]


def check_link_status(network, node_a, node_b):
    """Return the current status of a link, or not_found."""
    if not network.has_edge(node_a, node_b):
        return {
            "link": (node_a, node_b),
            "status": "not_found",
            "message": f"Link {node_a}-{node_b} does not exist.",
        }

    status = network[node_a][node_b].get("status", "up")
    return {
        "link": (node_a, node_b),
        "status": status,
        "message": f"Link {node_a}-{node_b} is {status}.",
    }


def get_active_network(network):
    """Return a copy of the graph with failed links removed."""
    active_network = network.copy()
    active_network.remove_edges_from(get_failed_links(active_network))
    return active_network


def find_available_route(network, source, destination):
    """Find the cheapest route using operational links only."""
    if source not in network or destination not in network:
        return {
            "path": None,
            "total_cost": None,
            "status": "unknown_node",
            "message": "Source or destination router does not exist.",
        }

    if source == destination:
        return {
            "path": [source],
            "total_cost": 0,
            "status": "available",
            "message": "Source and destination are the same router.",
        }

    active_network = get_active_network(network)

    for node_a, node_b, data in active_network.edges(data=True):
        cost = data.get("cost")
        if (
            isinstance(cost, bool)
            or not isinstance(cost, (int, float))
            or cost <= 0
        ):
            return {
                "path": None,
                "total_cost": None,
                "status": "invalid_cost",
                "message": f"Link {node_a}-{node_b} has an invalid cost.",
            }

    try:
        path = nx.dijkstra_path(
            active_network, source=source, target=destination, weight="cost"
        )
        total_cost = nx.path_weight(active_network, path, weight="cost")
        return {
            "path": path,
            "total_cost": total_cost,
            "status": "available",
            "message": "An operational route is available.",
        }
    except nx.NetworkXNoPath:
        return {
            "path": None,
            "total_cost": None,
            "status": "unreachable",
            "message": f"No operational route exists from {source} to {destination}.",
        }


def analyze_failure_impact(network, source, destinations):
    """Check reachability from a source to each requested destination."""
    results = {
        destination: find_available_route(network, source, destination)
        for destination in destinations
    }
    unreachable = [
        destination
        for destination, result in results.items()
        if result["status"] != "available"
    ]
    return {
        "source": source,
        "destinations": results,
        "unreachable_destinations": unreachable,
        "total_destinations": len(destinations),
        "unreachable_count": len(unreachable),
    }


def calculate_resilience(network, source, destinations):
    """Calculate the percentage of destinations that remain reachable."""
    impact = analyze_failure_impact(network, source, destinations)
    total = impact["total_destinations"]
    reachable = total - impact["unreachable_count"]
    return {
        "reachable_count": reachable,
        "total_destinations": total,
        "unreachable_destinations": impact["unreachable_destinations"],
        "reachability_percent": round(reachable / total * 100, 2) if total else 100.0,
    }


def compare_failure_scenario(network, source, destinations, failed_links):
    """Evaluate hypothetical failures on a copy, preserving the real graph."""
    scenario = deepcopy(network)
    for node_a, node_b in failed_links:
        fail_link(scenario, node_a, node_b)
    return {
        "failed_links": list(failed_links),
        "impact": analyze_failure_impact(scenario, source, destinations),
        "resilience": calculate_resilience(scenario, source, destinations),
    }


def detect_security_scenarios(network, utilization_threshold=80.0):
    """Flag marked suspicious nodes and links with high recorded utilization.

    This is a basic simulation heuristic, not proof of malicious activity.
    Link utilization is read from the optional utilization_mbps edge attribute.
    """
    if (
        isinstance(utilization_threshold, bool)
        or not isinstance(utilization_threshold, (int, float))
        or not 0 <= utilization_threshold <= 100
    ):
        raise ValueError("Utilization threshold must be between 0 and 100.")

    suspicious_nodes = [
        node for node, data in network.nodes(data=True)
        if data.get("suspicious", False)
    ]
    high_utilization_links = []

    for node_a, node_b, data in network.edges(data=True):
        capacity = data.get("capacity")
        utilization = data.get("utilization_mbps")
        if capacity is None or utilization is None:
            continue
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, (int, float))
            or capacity <= 0
            or isinstance(utilization, bool)
            or not isinstance(utilization, (int, float))
            or utilization < 0
        ):
            continue

        percentage = utilization / capacity * 100
        if percentage >= utilization_threshold:
            high_utilization_links.append({
                "link": (node_a, node_b),
                "utilization_mbps": utilization,
                "capacity_mbps": capacity,
                "utilization_percent": round(percentage, 2),
                "status": data.get("status", "up"),
            })

    return {
        "suspicious_nodes": suspicious_nodes,
        "high_utilization_links": high_utilization_links,
        "note": "High utilization is an indicator for investigation, not proof of malicious activity.",
    }


def recover_route(network, source, destination):
    """Return whether a route is currently available after any failures."""
    result = find_available_route(network, source, destination)
    if result["status"] == "available":
        return {
            "recovered": True,
            "path": result["path"],
            "total_cost": result["total_cost"],
            "message": "An operational route is available.",
        }
    return {
        "recovered": False,
        "path": None,
        "total_cost": None,
        "message": result.get("message", "Recovery failed: no operational route is available."),
    }
