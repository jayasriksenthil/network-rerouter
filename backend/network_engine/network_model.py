
import random
import networkx as nx


# 1. Initialize traffic tracking on the shared network
def initialize_link_utilization(network):
    for _, _, data in network.edges(data=True):
        data.setdefault("utilization_mbps", 0)


# 2. Create a traffic demand
def create_traffic_demand(source, destination, bandwidth_mbps):
    return {
        "source": source,
        "destination": destination,
        "bandwidth_mbps": bandwidth_mbps
    }


# 3. Generate random traffic demands
def generate_traffic_demands(network, number_of_demands):
    nodes = list(network.nodes())

    if len(nodes) < 2:
        return []

    demands = []

    for _ in range(number_of_demands):
        source, destination = random.sample(nodes, 2)

        demands.append(
            create_traffic_demand(
                source,
                destination,
                random.randint(10, 50)
            )
        )

    return demands


# 4. Validate a traffic demand
def validate_traffic_demand(network, demand):
    if not isinstance(demand, dict):
        return False

    source = demand.get("source")
    destination = demand.get("destination")
    bandwidth = demand.get("bandwidth_mbps")

    if source not in network or destination not in network:
        return False

    if source == destination:
        return False

    if not isinstance(bandwidth, (int, float)):
        return False

    return bandwidth > 0


# 5. Check whether every link on a route has enough capacity
def can_accommodate_traffic(network, path, bandwidth_mbps):
    if not path or bandwidth_mbps <= 0:
        return False

    for source, destination in zip(path, path[1:]):
        if not network.has_edge(source, destination):
            return False

        edge = network[source][destination]

        if edge.get("status") != "up":
            return False

        capacity = edge.get("capacity", 0)
        utilization = edge.get("utilization_mbps", 0)

        if capacity <= 0:
            return False

        if utilization + bandwidth_mbps > capacity:
            return False

    return True


# 6. Reserve capacity for a route
def reserve_capacity(network, path, bandwidth_mbps):
    if not can_accommodate_traffic(
        network, path, bandwidth_mbps
    ):
        return False

    for source, destination in zip(path, path[1:]):
        edge = network[source][destination]
        edge["utilization_mbps"] = (
            edge.get("utilization_mbps", 0) + bandwidth_mbps
        )

    return True


# 7. Release capacity when traffic ends
def release_capacity(network, path, bandwidth_mbps):
    if not path or bandwidth_mbps <= 0:
        return False

    # Validate the entire route before changing utilization.
    for source, destination in zip(path, path[1:]):
        if not network.has_edge(source, destination):
            return False

        current = network[source][destination].get(
            "utilization_mbps", 0
        )

        if current < bandwidth_mbps:
            return False

    for source, destination in zip(path, path[1:]):
        edge = network[source][destination]
        edge["utilization_mbps"] -= bandwidth_mbps

    return True


# 8. Detect congestion
def check_link_utilization(network, congestion_threshold=80):
    congested_links = []

    for source, destination, data in network.edges(data=True):
        capacity = data.get("capacity", 0)
        utilization = data.get("utilization_mbps", 0)

        if capacity <= 0:
            continue

        percentage = utilization / capacity * 100

        if percentage >= congestion_threshold:
            congested_links.append({
                "source": source,
                "destination": destination,
                "utilization_percent": round(percentage, 2),
                "overloaded": utilization > capacity
            })

    return congested_links


# 9. Check router trust
# Missing suspicious attribute defaults to False.
def is_router_trusted(network, router_id):
    return not network.nodes[router_id].get("suspicious", False)


# 10. Find the lowest-cost feasible route
def find_feasible_route(
    network, source, destination, bandwidth_mbps
):
    demand = create_traffic_demand(
        source, destination, bandwidth_mbps
    )

    if not validate_traffic_demand(network, demand):
        return None

    # Construct a temporary routing view.
    # The shared network remains the source of truth.
    routing_view = nx.Graph()

    for node, data in network.nodes(data=True):
        routing_view.add_node(node, **data)

    # Exclude suspicious routers.
    suspicious_routers = [
        node
        for node, data in routing_view.nodes(data=True)
        if data.get("suspicious", False)
    ]

    # Do not allow traffic to start from or end at a suspicious router.
    if source in suspicious_routers:
        return None

    if destination in suspicious_routers:
        return None

    routing_view.remove_nodes_from(suspicious_routers)

    # Exclude down links and links without enough remaining capacity.
    for u, v, data in network.edges(data=True):
        if data.get("status") != "up":
            continue

        capacity = data.get("capacity", 0)
        utilization = data.get("utilization_mbps", 0)

        if capacity <= 0:
            continue

        if utilization + bandwidth_mbps > capacity:
            continue

        routing_view.add_edge(u, v, **data)

    try:
        return nx.dijkstra_path(
            routing_view,
            source,
            destination,
            weight="cost"
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


# 11. Process one traffic demand
def process_traffic_demand(network, demand):
    if not validate_traffic_demand(network, demand):
        bandwidth = (
            demand.get("bandwidth_mbps", 0)
            if isinstance(demand, dict)
            else 0
        )

        return {
            "status": "invalid_demand",
            "path": None,
            "dropped_mbps": bandwidth
        }

    source = demand["source"]
    destination = demand["destination"]
    bandwidth = demand["bandwidth_mbps"]

    path = find_feasible_route(
        network, source, destination, bandwidth
    )

    if path is None:
        return {
            "status": "undelivered",
            "path": None,
            "dropped_mbps": bandwidth
        }

    # Revalidate and reserve capacity.
    if not reserve_capacity(network, path, bandwidth):
        return {
            "status": "undelivered",
            "path": None,
            "dropped_mbps": bandwidth
        }

    total_cost = sum(
        network[u][v]["cost"]
        for u, v in zip(path, path[1:])
    )

    return {
        "status": "delivered",
        "path": path,
        "total_cost": total_cost,
        "bandwidth_mbps": bandwidth,
        "dropped_mbps": 0
    }


# 12. Simulate multiple traffic demands
def simulate_traffic(network, demands):
    initialize_link_utilization(network)

    results = []

    for demand in demands:
        result = process_traffic_demand(network, demand)

        results.append({
            "demand": demand,
            "result": result
        })

    return results


# 13. Print current network utilization
def print_network_utilization(network):
    print("\nCurrent link utilization:")

    for source, destination, data in network.edges(data=True):
        utilization = data.get("utilization_mbps", 0)
        capacity = data.get("capacity", 0)

        print(
            f"{source} <-> {destination}: "
            f"{utilization} / {capacity} Mbps"
        )


# 14. Standalone test
# This example is for testing only.
# During integration, import and pass the network created by topology.py.
if __name__ == "__main__":
    from topology import create_network, add_router, add_link

    network = create_network()

    for router in ["A", "B", "C", "D"]:
        add_router(network, router)

    add_link(network, "A", "B", cost=1, capacity=100)
    add_link(network, "B", "D", cost=1, capacity=100)
    add_link(network, "A", "C", cost=2, capacity=80)
    add_link(network, "C", "D", cost=2, capacity=80)

    # Mark C as suspicious for testing the trust-aware feature.
    network.nodes["C"]["suspicious"] = True

    demands = [
        create_traffic_demand("A", "D", 20),
        create_traffic_demand("A", "D", 40),
        create_traffic_demand("B", "D", 30)
    ]

    results = simulate_traffic(network, demands)

    print("\nTraffic simulation results:")

    for item in results:
        print(item)

    print_network_utilization(network)

    print("\nCongested links:")

    for link in check_link_utilization(network):
        print(link)