
import unittest
import networkx as nx

from backend.network_engine.network_model import (
    create_traffic_demand,
    process_traffic_demand,
    reserve_capacity,
    release_capacity,
    check_link_utilization,
)


def make_network():
    graph = nx.Graph()

    for node in ["A", "B", "C", "D"]:
        graph.add_node(node, suspicious=False)

    graph.add_edge(
        "A", "B", cost=1, capacity=50,
        utilization_mbps=0, status="up"
    )
    graph.add_edge(
        "B", "D", cost=1, capacity=50,
        utilization_mbps=0, status="up"
    )
    graph.add_edge(
        "A", "C", cost=2, capacity=100,
        utilization_mbps=0, status="up"
    )
    graph.add_edge(
        "C", "D", cost=2, capacity=100,
        utilization_mbps=0, status="up"
    )

    return graph


class TestNetworkModel(unittest.TestCase):

    # Test 1: Choose the lowest-cost route
    def test_traffic_uses_lowest_cost_route(self):
        graph = make_network()

        result = process_traffic_demand(
            graph, create_traffic_demand("A", "D", 20)
        )

        self.assertTrue(result["delivered"])
        self.assertEqual(result["path"], ["A", "B", "D"])

    # Test 2: Reroute when the shortest route lacks capacity
    def test_capacity_limit_triggers_alternative_route(self):
        graph = make_network()
        graph["A"]["B"]["utilization_mbps"] = 40
        graph["B"]["D"]["utilization_mbps"] = 40

        result = process_traffic_demand(
            graph, create_traffic_demand("A", "D", 20)
        )

        self.assertTrue(result["delivered"])
        self.assertEqual(result["path"], ["A", "C", "D"])

    # Test 3: Avoid a suspicious router
    def test_suspicious_router_is_avoided(self):
        graph = make_network()
        graph.nodes["B"]["suspicious"] = True

        result = process_traffic_demand(
            graph, create_traffic_demand("A", "D", 20)
        )

        self.assertTrue(result["delivered"])
        self.assertNotIn("B", result["path"])

    # Test 4: Avoid a link that is down
    def test_down_link_is_avoided(self):
        graph = make_network()
        graph["A"]["B"]["status"] = "down"

        result = process_traffic_demand(
            graph, create_traffic_demand("A", "D", 20)
        )

        self.assertTrue(result["delivered"])
        self.assertEqual(result["path"], ["A", "C", "D"])

    # Test 5: Drop traffic when no route has enough capacity
    def test_no_capacity_means_dropped_traffic(self):
        graph = make_network()

        for u, v in graph.edges():
            graph[u][v]["capacity"] = 10

        result = process_traffic_demand(
            graph, create_traffic_demand("A", "D", 20)
        )

        self.assertFalse(result["delivered"])

    # Test 6: Reserve and release bandwidth
    def test_reserve_and_release_capacity(self):
        graph = make_network()
        path = ["A", "B", "D"]

        self.assertTrue(reserve_capacity(graph, path, 20))
        self.assertEqual(
            graph["A"]["B"]["utilization_mbps"], 20
        )

        release_capacity(graph, path, 20)

        self.assertEqual(
            graph["A"]["B"]["utilization_mbps"], 0
        )

    # Test 7: Detect an overloaded link
    def test_overloaded_link_is_reported(self):
        graph = make_network()
        graph["A"]["B"]["utilization_mbps"] = 60

        report = check_link_utilization(graph)

        link = next(
            item for item in report
            if item["link"] == ("A", "B")
        )

        self.assertEqual(link["status"], "overloaded")


if __name__ == "__main__":
    unittest.main()

