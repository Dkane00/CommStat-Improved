# Copyright (c) 2025 Manuel Ochoa
# This file is part of CommStat-Improved.
# Licensed under the GNU General Public License v3.0.

"""
Demo mode - plays back curated demo data for demonstration.

Two-part workflow:
1. Populate demo.db3 with test data (use demo_populate.py or manual entry)
2. Run: python startup.py --demo-mode 1

The demo reads from demo.db3 and writes to traffic.db3 with real timestamps,
paced over 60 seconds.
"""

import sqlite3
import os
from datetime import datetime
from PyQt5.QtCore import QTimer

DEMO_DATABASE = "demo.db3"
TRAFFIC_DATABASE = "traffic.db3"


def init_demo_database() -> str:
    """Initialize the demo database with required tables.

    Returns:
        Path to the demo database
    """
    if os.path.exists(DEMO_DATABASE):
        print(f"Using existing demo database: {DEMO_DATABASE}")
        return DEMO_DATABASE

    print(f"Creating demo database: {DEMO_DATABASE}")

    with sqlite3.connect(DEMO_DATABASE, timeout=10) as conn:
        # Scenarios table - stores version info
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_scenarios (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            )
        """)

        # Demo statreps - no datetime, that's generated at playback
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_statreps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                sequence_order INTEGER NOT NULL,
                callsign TEXT NOT NULL,
                groupname TEXT,
                grid TEXT,
                status TEXT,
                commpwr TEXT,
                pubwtr TEXT,
                med TEXT,
                ota TEXT,
                trav TEXT,
                net TEXT,
                fuel TEXT,
                food TEXT,
                crime TEXT,
                civil TEXT,
                political TEXT,
                comments TEXT,
                FOREIGN KEY (scenario_id) REFERENCES demo_scenarios(id)
            )
        """)

        # Demo messages - no datetime
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                sequence_order INTEGER NOT NULL,
                callsign TEXT NOT NULL,
                groupid TEXT,
                message TEXT,
                FOREIGN KEY (scenario_id) REFERENCES demo_scenarios(id)
            )
        """)

        conn.commit()

    return DEMO_DATABASE


def get_scenario_info(version: int) -> dict:
    """Get scenario name and description.

    Args:
        version: Scenario ID

    Returns:
        Dict with 'name' and 'description', or defaults if not found
    """
    if not os.path.exists(DEMO_DATABASE):
        return {"name": f"Scenario {version}", "description": "No demo database found"}

    with sqlite3.connect(DEMO_DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT name, description FROM demo_scenarios WHERE id = ?",
            (version,)
        ).fetchone()

        if row:
            return {"name": row["name"], "description": row["description"]}
        return {"name": f"Scenario {version}", "description": "Scenario not defined"}


def get_demo_statreps(version: int) -> list:
    """Get all statreps for a scenario, ordered by sequence.

    Args:
        version: Scenario ID

    Returns:
        List of statrep dicts
    """
    if not os.path.exists(DEMO_DATABASE):
        return []

    with sqlite3.connect(DEMO_DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM demo_statreps
               WHERE scenario_id = ?
               ORDER BY sequence_order""",
            (version,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_demo_messages(version: int) -> list:
    """Get all messages for a scenario, ordered by sequence.

    Args:
        version: Scenario ID

    Returns:
        List of message dicts
    """
    if not os.path.exists(DEMO_DATABASE):
        return []

    with sqlite3.connect(DEMO_DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM demo_messages
               WHERE scenario_id = ?
               ORDER BY sequence_order""",
            (version,)
        ).fetchall()
        return [dict(row) for row in rows]


def write_statrep_to_traffic(statrep: dict) -> None:
    """Write a statrep to the traffic database with current timestamp.

    Args:
        statrep: Dict with statrep fields (no datetime)
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    srid = f"DEMO{statrep['id']:04d}"

    with sqlite3.connect(TRAFFIC_DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO StatRep_Data(
                datetime, callsign, groupname, grid, SRid, prec,
                status, commpwr, pubwtr, med, ota, trav, net,
                fuel, food, crime, civil, political, comments, source, frequency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            statrep.get("callsign", ""),
            statrep.get("groupname", ""),
            statrep.get("grid", ""),
            srid,
            "2",  # precedence
            statrep.get("status", "1"),
            statrep.get("commpwr", "1"),
            statrep.get("pubwtr", "1"),
            statrep.get("med", "1"),
            statrep.get("ota", "1"),
            statrep.get("trav", "1"),
            statrep.get("net", "1"),
            statrep.get("fuel", "1"),
            statrep.get("food", "1"),
            statrep.get("crime", "1"),
            statrep.get("civil", "1"),
            statrep.get("political", "1"),
            statrep.get("comments", "DEMO MODE"),
            1,  # source
            7078000  # frequency
        ))
        conn.commit()


def write_message_to_traffic(message: dict) -> None:
    """Write a message to the traffic database with current timestamp.

    Args:
        message: Dict with message fields (no datetime)
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(TRAFFIC_DATABASE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO messages_Data(datetime, groupid, idnum, callsign, message, frequency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            now,
            message.get("groupid", ""),
            message.get("id", 0),
            message.get("callsign", ""),
            message.get("message", ""),
            7078000
        ))
        conn.commit()


def cleanup_demo_data_from_traffic() -> None:
    """Remove demo-generated records from traffic database."""
    with sqlite3.connect(TRAFFIC_DATABASE, timeout=10) as conn:
        conn.execute("DELETE FROM StatRep_Data WHERE comments = 'DEMO MODE'")
        conn.execute("DELETE FROM StatRep_Data WHERE SRid LIKE 'DEMO%'")
        conn.execute("DELETE FROM messages_Data WHERE callsign LIKE 'DEMO%'")
        conn.commit()


class DemoRunner:
    """Plays back demo data from demo.db3 to traffic.db3 over configurable duration."""

    def __init__(self, main_window, version: int = 1, duration: int = 60):
        """Initialize demo runner.

        Args:
            main_window: Reference to MainWindow for UI refresh
            version: Demo scenario version (1, 2, 3, etc.)
            duration: Playback duration in seconds (default 60)
        """
        self.window = main_window
        self.version = version
        self.duration = duration
        self.scenario = get_scenario_info(version)

        # Load all demo data
        self.statreps = get_demo_statreps(version)
        self.messages = get_demo_messages(version)

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.elapsed = 0
        self.statrep_index = 0
        self.message_index = 0

        # Calculate pacing - spread items over duration
        self.total_items = len(self.statreps) + len(self.messages)

    def start(self) -> None:
        """Start the demo playback."""
        print(f"Demo mode starting: {self.scenario['name']}")
        print(f"Description: {self.scenario['description']}")
        print(f"Playing {len(self.statreps)} statreps and {len(self.messages)} messages over {self.duration} seconds")

        if self.total_items == 0:
            print("Warning: No demo data found for this scenario")
            print(f"Populate {DEMO_DATABASE} with scenario_id={self.version}")
            return

        # Clear any previous demo data from traffic db
        cleanup_demo_data_from_traffic()

        self.timer.start(2000)  # tick every 2 seconds (30 ticks in 60 seconds)
        self._tick()  # initial tick

    def _tick(self) -> None:
        """Called every 2 seconds during demo playback."""
        self.elapsed += 2

        if self.elapsed > self.duration:
            self.timer.stop()
            print("Demo playback complete")
            return

        # Calculate how many items should be shown by now
        progress = self.elapsed / float(self.duration)
        target_statreps = int(progress * len(self.statreps))
        target_messages = int(progress * len(self.messages))

        # Write statreps up to target
        while self.statrep_index < target_statreps and self.statrep_index < len(self.statreps):
            statrep = self.statreps[self.statrep_index]
            write_statrep_to_traffic(statrep)
            print(f"  StatRep: {statrep['callsign']} in {statrep['grid']}")
            self.statrep_index += 1

        # Write messages up to target
        while self.message_index < target_messages and self.message_index < len(self.messages):
            message = self.messages[self.message_index]
            write_message_to_traffic(message)
            print(f"  Message: {message['callsign']}: {message['message'][:40]}...")
            self.message_index += 1

        # Refresh UI
        self.window._load_statrep_data()
        self.window._load_message_data()
        self.window._save_map_position(callback=self.window._load_map)
