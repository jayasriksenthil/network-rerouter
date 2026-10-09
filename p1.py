
import networkx as nx
from failure_recovery import fail_link, check_link_status

# Create a small test network
network = nx.Graph()
network.add_edge("A", "B", cost=5, capacity=100, status="up")
network.add_edge("B", "C", cost=3, capacity=100, status="up")

print("1. Checking link before failure:")
print(check_link_status(network, "A", "B"))

print("\n2. Simulating link failure...")
print(fail_link(network, "A", "B"))

print("\n3. Checking link after failure:")
print(check_link_status(network, "A", "B"))

print("\nTest completed!")
