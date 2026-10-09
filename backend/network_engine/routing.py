
import networkx as nx


def find_best_route(network, source, destination):
    

    # 1. Validate the source and destination
    if source not in network:
        return {
            "path": [],
            "total_cost": None,
            "status": "error",
            "message": f"Source router '{source}' does not exist."
        }

    if destination not in network:
        return {
            "path": [],
            "total_cost": None,
            "status": "error",
            "message": f"Destination router '{destination}' does not exist."
        }

    # 2. Handle the case where source and destination are identical
    if source == destination:
        return {
            "path": [source],
            "total_cost": 0,
            "status": "success",
            "message": "Source and destination are the same router."
        }

    # 3. Build a temporary graph containing only working links
    active_network = nx.Graph()
    active_network.add_nodes_from(network.nodes(data=True))

    for router_a, router_b, data in network.edges(data=True):
        if data.get("status", "up") == "up":
            cost = data.get("cost")

            # Every active link must have a valid positive cost
            if (
                not isinstance(cost, (int, float))
                or isinstance(cost, bool)
                or cost <= 0
            ):
                return {
                    "path": [],
                    "total_cost": None,
                    "status": "error",
                    "message": (
                        f"Link {router_a}-{router_b} "
                        "has an invalid cost."
                    )
                }

            active_network.add_edge(
                router_a,
                router_b,
                **data
            )

    # 4. Use Dijkstra's algorithm to find the minimum-cost route
    try:
        path = nx.dijkstra_path(
            active_network,
            source=source,
            target=destination,
            weight="cost"
        )

        # 5. Calculate the total cost of the selected route
        total_cost = sum(
            active_network[path[i]][path[i + 1]]["cost"]
            for i in range(len(path) - 1)
        )

        return {
            "path": path,
            "total_cost": total_cost,
            "status": "success",
            "message": "Best route found."
        }

    except nx.NetworkXNoPath:
        return {
            "path": [],
            "total_cost": None,
            "status": "unreachable",
            "message": (
                f"No working route exists from "
                f"{source} to {destination}."
            )
        }



if __name__ == "__main__":
    from backend.network_engine.topology import (
        create_network,
        add_router,
        add_link,
    )

    network = create_network()

    for router in ["A", "B", "C", "D"]:
        add_router(network, router)

    add_link(network, "A", "B", cost=1, capacity=100)
    add_link(network, "B", "D", cost=1, capacity=100)
    add_link(network, "A", "C", cost=2, capacity=80)
    add_link(network, "C", "D", cost=2, capacity=80)

    print("\nTEST 1: Normal network")
    print(find_best_route(network, "A", "D"))

    network["B"]["D"]["status"] = "down"

    print("\nTEST 2: Link B-D fails")
    print(find_best_route(network, "A", "D"))

    network["C"]["D"]["status"] = "down"

    print("\nTEST 3: Both routes blocked")
    print(find_best_route(network, "A", "D"))



# TEST 7: Choose the cheapest route
network = create_network()

for router in ["A", "B", "C", "D"]:
    add_router(network, router)

add_link(network, "A", "B", cost=1, capacity=100)
add_link(network, "B", "D", cost=1, capacity=100)
add_link(network, "A", "C", cost=2, capacity=80)
add_link(network, "C", "D", cost=2, capacity=80)

result = find_best_route(network, "A", "D")

print("\nTEST 7 - Cheapest route:", result)

assert result["path"] == ["A", "B", "D"]
assert result["total_cost"] == 2

print("Cheapest route test passed!")