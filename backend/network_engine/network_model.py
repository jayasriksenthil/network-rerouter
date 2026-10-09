
import random
import networkx as nx

from backend.network_engine.routing import find_best_route


# --------------------------------------------------
# MILESTONE 1: NETWORK MODEL AND TRAFFIC STRUCTURE
# --------------------------------------------------

def initialize_link_utilization(network):
    """Initialize traffic utilization on every link."""
    for _, _, data in network.edges(data=True):
        data.setdefault("utilization_mbps", 0.0)


def create_traffic_demand(source, destination, bandwidth_mbps):
    """Create one traffic request."""
    return {
        "source": source,
        "destination": destination,
        "bandwidth_mbps": float(bandwidth_mbps),
    }


def validate_traffic_demand(network, demand):
    """Validate endpoints and requested bandwidth."""
    if not isinstance(demand, dict):
        raise ValueError("Demand must be a dictionary.")

    source = demand.get("source")
    destination = demand.get("destination")
    bandwidth = demand.get("bandwidth_mbps")

    if source not in network or destination not in network:
        raise ValueError("Source and destination must exist.")

    if source == destination:
        raise ValueError("Source and destination must differ.")

    if isinstance(bandwidth, bool) or not isinstance(
        bandwidth, (int, float)
    ):
        raise ValueError("Bandwidth must be a number.")

    if not 0 < bandwidth < float("inf"):
        raise ValueError("Bandwidth must be finite and positive.")


# --------------------------------------------------
# MILESTONE 2: TRAFFIC SIMULATION
# --------------------------------------------------

def generate_traffic_demands(
    network,
    number_of_demands,
    min_bandwidth=5,
    max_bandwidth=40,
    seed=None,
):
    """Generate reproducible random traffic demands."""
    if number_of_demands < 0:
        raise ValueError("Number of demands cannot be negative.")

    if min_bandwidth <= 0 or max_bandwidth < min_bandwidth:
        raise ValueError("Invalid bandwidth range.")

    nodes = list(network.nodes())
    if len(nodes) < 2:
        return []

    rng = random.Random(seed)
    demands = []

    for _ in range(number_of_demands):
        source, destination = rng.sample(nodes, 2)
        bandwidth = rng.randint(min_bandwidth, max_bandwidth)

        demands.append(
            create_traffic_demand(source, destination, bandwidth)
        )

    return demands


# --------------------------------------------------
# MILESTONE 3: CAPACITY MANAGEMENT
# --------------------------------------------------

def get_link_remaining_capacity(data):
    """Return available bandwidth on a link."""
    capacity = float(data.get("capacity", 0))
    utilization = float(data.get("utilization_mbps", 0))

    return max(0.0, capacity - utilization)


def can_accommodate_traffic(network, path, bandwidth_mbps):
    """Check every link on a candidate path."""
    if not path or len(path) < 2:
        return False

    for u, v in zip(path, path[1:]):
        if not network.has_edge(u, v):
            return False

        data = network[u][v]

        if data.get("status", "up") != "up":
            return False

        capacity = data.get("capacity")
        utilization = data.get("utilization_mbps", 0)

        if capacity is None or capacity <= 0:
            return False

        if utilization < 0 or utilization > capacity:
            return False

        if get_link_remaining_capacity(data) < bandwidth_mbps:
            return False

    return True


def reserve_capacity(network, path, bandwidth_mbps):
    """Reserve bandwidth on all links, or reserve nothing."""
    if bandwidth_mbps <= 0:
        raise ValueError("Bandwidth must be positive.")

    if not can_accommodate_traffic(
        network, path, bandwidth_mbps
    ):
        return False

    # Check all links first, then update them.
    for u, v in zip(path, path[1:]):
        network[u][v]["utilization_mbps"] = (
            network[u][v].get("utilization_mbps", 0)
            + bandwidth_mbps
        )

    return True


def release_capacity(network, path, bandwidth_mbps):
    """Release bandwidth when a simulated flow finishes."""
    if bandwidth_mbps <= 0:
        raise ValueError("Bandwidth must be positive.")

    if not path or len(path) < 2:
        raise ValueError("A valid path is required.")

    # Validate the whole release before modifying any link.
    for u, v in zip(path, path[1:]):
        if not network.has_edge(u, v):
            raise ValueError(f"Link {u}-{v} does not exist.")

        utilization = network[u][v].get("utilization_mbps", 0)

        if utilization < bandwidth_mbps:
            raise ValueError(
                f"Cannot release more bandwidth than reserved on {u}-{v}."
            )

    for u, v in zip(path, path[1:]):
        network[u][v]["utilization_mbps"] = max(
            0.0,
            network[u][v].get("utilization_mbps", 0)
            - bandwidth_mbps,
        )


def check_link_utilization(network, overload_threshold=0.8):
    """Report link utilization and congestion status."""
    if not 0 < overload_threshold <= 1:
        raise ValueError("Threshold must be in (0, 1].")

    reports = []

    for u, v, data in network.edges(data=True):
        capacity = float(data.get("capacity", 0))
        utilization = float(data.get("utilization_mbps", 0))

        ratio = utilization / capacity if capacity > 0 else None

        if capacity <= 0:
            status = "invalid_capacity"
        elif utilization > capacity:
            status = "overloaded"
        elif ratio >= overload_threshold:
            status = "congested"
        else:
            status = "normal"

        reports.append({
            "link": (u, v),
            "capacity_mbps": capacity,
            "utilization_mbps": utilization,
            "remaining_mbps": max(0.0, capacity - utilization),
            "utilization_ratio": ratio,
            "status": status,
        })

    return reports


# --------------------------------------------------
# MILESTONE 4: TRUST- AND CAPACITY-AWARE REROUTING
# --------------------------------------------------

def build_feasible_network(
    network, bandwidth_mbps, source, destination
):
    """
    Build a temporary graph containing only eligible links
    and trusted intermediate routers.
    """
    eligible = nx.Graph()

    if source not in network or destination not in network:
        return eligible

    # Do not send traffic through suspicious endpoints either.
    if network.nodes[source].get("suspicious", False):
        return eligible

    if network.nodes[destination].get("suspicious", False):
        return eligible

    for node, attributes in network.nodes(data=True):
        if not attributes.get("suspicious", False):
            eligible.add_node(node, **attributes)

    for u, v, data in network.edges(data=True):
        if u not in eligible or v not in eligible:
            continue

        if data.get("status", "up") != "up":
            continue

        if data.get("cost", 0) <= 0:
            continue

        if get_link_remaining_capacity(data) < bandwidth_mbps:
            continue

        eligible.add_edge(u, v, **data)

    return eligible


def find_feasible_route(
    network, source, destination, bandwidth_mbps
):
    """
    Ask Member 1's routing engine for the cheapest feasible
    route. Return the route result and the eligible graph.
    """
    if source not in network or destination not in network:
        return {
            "path": [],
            "total_cost": None,
            "status": "error",
            "message": "Unknown source or destination.",
        }, None

    if source == destination:
        return {
            "path": [],
            "total_cost": 0,
            "status": "error",
            "message": "Source and destination must differ.",
        }, None

    if bandwidth_mbps <= 0:
        return {
            "path": [],
            "total_cost": None,
            "status": "error",
            "message": "Bandwidth must be positive.",
        }, None

    eligible = build_feasible_network(
        network, bandwidth_mbps, source, destination
    )

    if source not in eligible or destination not in eligible:
        return {
            "path": [],
            "total_cost": None,
            "status": "unreachable",
            "message": "An endpoint is untrusted or unavailable.",
        }, eligible

    result = find_best_route(eligible, source, destination)

    if result.get("status") != "success":
        return result, eligible

    path = result.get("path", [])

    # Defensive recheck against the original shared graph.
    if not can_accommodate_traffic(
        network, path, bandwidth_mbps
    ):
        return {
            "path": [],
            "total_cost": None,
            "status": "unreachable",
            "message": "No capacity-feasible route is available.",
        }, eligible

    return result, eligible


# --------------------------------------------------
# MILESTONE 5: PROCESS AND INTEGRATE DEMANDS
# --------------------------------------------------

def process_traffic_demand(network, demand):
    """Route a demand and reserve bandwidth if accepted."""
    initialize_link_utilization(network)

    try:
        validate_traffic_demand(network, demand)
    except (ValueError, TypeError) as error:
        return {
            "delivered": False,
            "path": [],
            "bandwidth_mbps": demand.get("bandwidth_mbps")
            if isinstance(demand, dict) else None,
            "reason": str(error),
        }

    source = demand["source"]
    destination = demand["destination"]
    bandwidth = float(demand["bandwidth_mbps"])

    result, _ = find_feasible_route(
        network, source, destination, bandwidth
    )

    if result.get("status") != "success":
        return {
            "delivered": False,
            "path": [],
            "bandwidth_mbps": bandwidth,
            "reason": result.get(
                "message", "No feasible route."
            ),
        }

    path = result.get("path", [])

    # Reserve on the real shared graph only after route selection.
    if not reserve_capacity(network, path, bandwidth):
        return {
            "delivered": False,
            "path": [],
            "bandwidth_mbps": bandwidth,
            "reason": "Capacity changed before reservation.",
        }

    return {
        "delivered": True,
        "path": path,
        "total_cost": result.get("total_cost"),
        "bandwidth_mbps": bandwidth,
        "reason": "Traffic accepted and capacity reserved.",
    }


def simulate_traffic(network, demands):
    """Process a list of demands and calculate drop statistics."""
    initialize_link_utilization(network)

    results = []

    for demand in demands:
        result = process_traffic_demand(network, demand)
        results.append({
            "demand": demand,
            **result,
        })

    accepted = sum(r["delivered"] for r in results)
    dropped = len(results) - accepted
    total = len(results)

    return {
        "results": results,
        "total_demands": total,
        "accepted": accepted,
        "dropped": dropped,
        "delivery_rate_percent": (
            accepted * 100 / total if total else 0.0
        ),
        "drop_rate_percent": (
            dropped * 100 / total if total else 0.0
        ),
        "link_utilization": check_link_utilization(network),
    }


# --------------------------------------------------
# MILESTONE 6: DEMONSTRATION SCENARIO
# --------------------------------------------------

def run_demo():
    """Demonstrate capacity-aware rerouting and trust checks."""
    network = nx.Graph()

    for router in ["A", "B", "C", "D"]:
        network.add_node(router, suspicious=False)

    # Short route: A-B-D, capacity 50 Mbps per link.
    network.add_edge(
        "A", "B", cost=1, capacity=50,
        utilization_mbps=0, status="up"
    )
    network.add_edge(
        "B", "D", cost=1, capacity=50,
        utilization_mbps=0, status="up"
    )

    # Alternative route: A-C-D, capacity 100 Mbps per link.
    network.add_edge(
        "A", "C", cost=2, capacity=100,
        utilization_mbps=0, status="up"
    )
    network.add_edge(
        "C", "D", cost=2, capacity=100,
        utilization_mbps=0, status="up"
    )

    demands = [
        create_traffic_demand("A", "D", 40),
        create_traffic_demand("A", "D", 30),
        create_traffic_demand("A", "D", 20),
    ]

    print("=== Initial traffic simulation ===")
    summary = simulate_traffic(network, demands)

    for item in summary["results"]:
        print(item)

    print("\n=== Summary ===")
    print(
        f"Accepted: {summary['accepted']}, "
        f"Dropped: {summary['dropped']}, "
        f"Drop rate: {summary['drop_rate_percent']:.1f}%"
    )

    print("\n=== Link utilization ===")
    for link in summary["link_utilization"]:
        print(link)

    print("\n=== Trust-aware rerouting ===")
    network.nodes["B"]["suspicious"] = True

    result = process_traffic_demand(
        network, create_traffic_demand("A", "D", 10)
    )
    print(result)


if __name__ == "__main__":
    run_demo()
