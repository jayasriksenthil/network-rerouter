
import networkx as nx


def create_network():
    
    return nx.Graph()


def add_router(network, router_id):
    
    router_id = router_id.strip()

    if not router_id:
        raise ValueError("Router ID cannot be empty.")

    if router_id in network:
        raise ValueError(f"Router {router_id} already exists.")

    network.add_node(router_id)
    print(f"Router {router_id} added.")


def add_link(network, router_a, router_b, cost, capacity):
    
    if router_a not in network or router_b not in network:
        raise ValueError("Add both routers before connecting them.")

    if router_a == router_b:
        raise ValueError("A router cannot link to itself.")

    if network.has_edge(router_a, router_b):
        raise ValueError("These routers are already connected.")

    if cost <= 0 or capacity <= 0:
        raise ValueError("Cost and capacity must be positive.")

    network.add_edge(
        router_a,
        router_b,
        cost=cost,
        capacity=capacity,
        status="up",
    )
    print(f"Link {router_a} <-> {router_b} added.")


def remove_link(network, router_a, router_b):
    
    if not network.has_edge(router_a, router_b):
        raise ValueError("That link does not exist.")

    network.remove_edge(router_a, router_b)
    print(f"Link {router_a} <-> {router_b} removed.")


if __name__ == "__main__":
    network = create_network()

    # Create routers dynamically
    for router in ["A", "B", "C", "D"]:
        add_router(network, router)

    # Create connections dynamically
    add_link(network, "A", "B", cost=1, capacity=100)
    add_link(network, "B", "D", cost=1, capacity=100)
    add_link(network, "A", "C", cost=2, capacity=80)
    add_link(network, "C", "D", cost=2, capacity=80)

    print("\nRouters:", list(network.nodes))
    print("Links:", list(network.edges(data=True)))
