
import json
import sqlite3
from pathlib import Path

import networkx as nx


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "sentinelroute.db"


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------
def init_db():
    """Create the database table if it does not exist."""

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


# --------------------------------------------------
# SAVE NETWORK
# --------------------------------------------------
def save_network(name, network):
    """Save or update a network in the SQLite database."""

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


# --------------------------------------------------
# LIST SAVED NETWORKS
# --------------------------------------------------
def list_saved_networks():
    """Return the names of all saved networks."""

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


# --------------------------------------------------
# LOAD NETWORK
# --------------------------------------------------
def load_network(name):
    """Load a saved network and return it as a NetworkX graph."""

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
