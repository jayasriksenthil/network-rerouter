import json
import sqlite3
from pathlib import Path

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "sentinelroute.db"


def init_db():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_networks (
                name TEXT PRIMARY KEY,
                graph_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_network(name, network):
    name = name.strip()

    if not name:
        raise ValueError("Network name cannot be empty.")

    graph_data = nx.node_link_data(network)
    graph_json = json.dumps(graph_data)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO saved_networks
                (name, graph_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                graph_json = excluded.graph_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, graph_json),
        )


def list_saved_networks():
    init_db()

    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM saved_networks
            ORDER BY name
            """
        ).fetchall()

    return [row[0] for row in rows]


def load_network(name):
    init_db()

    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            """
            SELECT graph_json
            FROM saved_networks
            WHERE name = ?
            """,
            (name,),
        ).fetchone()

    if row is None:
        raise ValueError(
            f"Saved network '{name}' was not found."
        )

    graph_data = json.loads(row[0])
    return nx.node_link_graph(graph_data)