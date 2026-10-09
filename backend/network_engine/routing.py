import networkx as nx


def find_best_route(network, source, destination):
    if source not in network:
        return {
            "status": "error",
            "path": None,
            "total_cost": None,
            "message": f"Source router '{source}' does not exist.",
        }

    if destination not in network:
        return {
            "status": "error",
            "path": None,
            "total_cost": None,
            "message": f"Destination router '{destination}' does not exist.",
        }

    if source == destination:
        return {
            "status": "success",
            "path": [source],
            "total_cost": 0,
            "message": "Source and destination are the same.",
        }

    active_network = nx.Graph()
    active_network.add_nodes_from(network.nodes(data=True))

    for a, b, data in network.edges(data=True):
        if data.get("status", "up") == "up":
            cost = data.get("cost", 1)

            if (
                isinstance(cost, bool)
                or not isinstance(cost, (int, float))
                or cost <= 0
            ):
                return {
                    "status": "error",
                    "path": None,
                    "total_cost": None,
                    "message": f"Invalid cost on link {a}-{b}.",
                }

            active_network.add_edge(a, b, cost=cost)

    try:
        path = nx.dijkstra_path(
            active_network,
            source,
            destination,
            weight="cost",
        )

        total_cost = nx.path_weight(
            active_network,
            path,
            weight="cost",
        )

        return {
            "status": "success",
            "path": path,
            "total_cost": total_cost,
            "message": "Best route found successfully.",
        }

    except nx.NetworkXNoPath:
        return {
            "status": "unreachable",
            "path": None,
            "total_cost": None,
            "message": "No operational route is available.",
        }
