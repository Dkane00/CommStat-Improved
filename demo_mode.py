# Copyright (c) 2025 Manuel Ochoa
# This file is part of CommStat-Improved.
# Licensed under the GNU General Public License v3.0.

"""
Demo mode - generates sample disaster simulation data for demonstration.

Usage: python startup.py --demo-mode
"""

import sqlite3
import random
from datetime import datetime
from PyQt5.QtCore import QTimer

DATABASE_FILE = "traffic.db3"

# Sample callsigns for demo
CALLSIGNS = [
    "N0DDK", "K5ABC", "W1AW", "KG7MXX", "WA6ABC",
    "N7XYZ", "K0DEF", "W3GHI", "KA2JKL", "WB6MNO",
    "KC8QQQ", "W4RRR", "N1SSS", "K6TTT", "WA9UUU",
    "KD7VVV", "W2WWW", "N5YYY", "K3ZZZ", "WB4AAA",
]

# Grid squares by zone
COASTAL_WEST_GRIDS = [
    "CM93", "CM94", "CM95", "CM97", "CM98",
    "CN70", "CN80", "CN81", "CN82", "CN83", "CN84", "CN85", "CN86", "CN87", "CN88",
]

COASTAL_NORTHEAST_GRIDS = [
    "FN41", "FN42", "FN43", "FN44", "FN31", "FN32", "FN30", "FM29", "FM19",
]

INLAND_WEST_GRIDS = ["DM04", "DM13", "DM14", "DM26", "DN07", "DN17", "DN31"]

INLAND_NORTHEAST_GRIDS = ["FN20", "FN21", "FN10", "FN11", "EN92", "EN91"]

CENTRAL_GRIDS = [
    "EM10", "EM12", "EM13", "DM91", "DM92",  # Texas
    "EN72", "EN73", "EN82", "EN83",  # Michigan
    "EM17", "EM27", "EM28", "EM29", "EN10", "EN20",  # Central states
]

# Zone-specific field weights (red=3, yellow=2, green=1)
COASTAL_WEIGHTS = {
    "power":    {"3": 70, "2": 20, "1": 10},
    "water":    {"3": 60, "2": 30, "1": 10},
    "medical":  {"3": 50, "2": 30, "1": 20},
    "travel":   {"3": 80, "2": 15, "1": 5},
    "comms":    {"3": 40, "2": 40, "1": 20},
    "food":     {"3": 30, "2": 40, "1": 30},
    "crime":    {"3": 40, "2": 30, "1": 30},
    "internet": {"3": 90, "2": 10, "1": 0},
}

INLAND_WEIGHTS = {
    "power":    {"3": 30, "2": 50, "1": 20},
    "water":    {"3": 20, "2": 40, "1": 40},
    "medical":  {"3": 20, "2": 30, "1": 50},
    "travel":   {"3": 40, "2": 40, "1": 20},
    "comms":    {"3": 20, "2": 40, "1": 40},
    "food":     {"3": 10, "2": 30, "1": 60},
    "crime":    {"3": 20, "2": 30, "1": 50},
    "internet": {"3": 50, "2": 30, "1": 20},
}

CENTRAL_WEIGHTS = {
    "power":    {"3": 0, "2": 10, "1": 90},
    "water":    {"3": 0, "2": 10, "1": 90},
    "medical":  {"3": 0, "2": 10, "1": 90},
    "travel":   {"3": 0, "2": 10, "1": 90},
    "comms":    {"3": 0, "2": 10, "1": 90},
    "food":     {"3": 0, "2": 5, "1": 95},
    "crime":    {"3": 0, "2": 10, "1": 90},
    "internet": {"3": 0, "2": 10, "1": 90},
}

# Comments by zone (ALL CAPS - JS8Call format)
COASTAL_COMMENTS = [
    "EARTHQUAKE DAMAGE REQUESTING ASSISTANCE",
    "TSUNAMI WARNING IN EFFECT",
    "POWER OUT NO ETA FOR RESTORE",
    "ROADS FLOODED IMPASSABLE",
    "MAJOR STRUCTURAL DAMAGE",
    "FIRES REPORTED MULTIPLE LOCATIONS",
    "WATER MAIN BREAK NO WATER",
    "BRIDGE COLLAPSED DETOUR REQUIRED",
    "GAS LEAK EVACUATING AREA",
    "EMERGENCY SERVICES OVERWHELMED",
]

INLAND_COMMENTS = [
    "MINOR DAMAGE SOME POWER OUTAGES",
    "ROADS OPEN WITH DELAYS",
    "SHELTERS OPENING NEARBY",
    "SOME CELL SERVICE RESTORED",
    "POWER FLICKERING UNSTABLE",
    "TRAFFIC HEAVY FROM EVACUEES",
    "STORES LOW ON SUPPLIES",
    "HOSPITAL ACCEPTING PATIENTS",
]

CENTRAL_COMMENTS = [
    "ALL CLEAR NO ISSUES",
    "NORMAL CONDITIONS",
    "WEEKLY CHECKIN ALL OK",
    "STANDING BY TO ASSIST",
    "NO DAMAGE REPORTED",
    "READY TO RELAY TRAFFIC",
]

# Messages (ALL CAPS - JS8Call format)
DEMO_MESSAGES = [
    "NEED MEDICAL SUPPLIES URGENT",
    "EVACUATION ROUTE BLOCKED",
    "SHELTER AT HIGH SCHOOL OPEN",
    "WATER DISTRIBUTION AT CITY HALL",
    "GRID DOWN COUNTY WIDE",
    "AFTERSHOCK REPORTED 4.2",
    "NATIONAL GUARD ARRIVING",
    "CELL TOWERS DOWN USE HF",
    "HOSPITAL AT CAPACITY",
    "ROADS CLEAR TO EAST",
]

GROUPS = ["MAGNET", "AMRRON", "PREPPERNET"]


def get_status_by_weight(weights: dict) -> str:
    """Return status based on weighted probability.

    Args:
        weights: dict like {"1": 90, "2": 10, "3": 0} for green/yellow/red %

    Returns:
        Status string "1", "2", or "3"
    """
    roll = random.randint(1, 100)
    cumulative = 0
    for status, weight in weights.items():
        cumulative += weight
        if roll <= cumulative:
            return status
    return "1"  # default green


def insert_demo_statrep(callsign: str, grid: str, group: str, zone: str = "central") -> None:
    """Insert a demo statrep with mixed field statuses.

    Args:
        callsign: Amateur callsign
        grid: 4-char Maidenhead grid
        group: Group name (MAGNET, AMRRON, etc.)
        zone: "coastal", "inland", or "central"
    """
    weights = {
        "coastal": COASTAL_WEIGHTS,
        "inland": INLAND_WEIGHTS,
    }.get(zone, CENTRAL_WEIGHTS)

    comments = {
        "coastal": COASTAL_COMMENTS,
        "inland": INLAND_COMMENTS,
    }.get(zone, CENTRAL_COMMENTS)

    # Generate each field independently
    power = get_status_by_weight(weights["power"])
    water = get_status_by_weight(weights["water"])
    medical = get_status_by_weight(weights["medical"])
    travel = get_status_by_weight(weights["travel"])
    comms = get_status_by_weight(weights["comms"])
    food = get_status_by_weight(weights["food"])
    crime = get_status_by_weight(weights["crime"])
    internet = get_status_by_weight(weights["internet"])

    # Overall status = worst of all fields
    overall = max(power, water, medical, travel, comms, food, crime, internet)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    srid = f"DEMO{random.randint(1000, 9999)}"
    comment = random.choice(comments)

    with sqlite3.connect(DATABASE_FILE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO StatRep_Data(
                datetime, callsign, groupname, grid, SRid, prec,
                status, commpwr, pubwtr, med, ota, trav, net,
                fuel, food, crime, civil, political, comments, source, frequency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, callsign, group, grid, srid, "2",  # scope=community
            overall, power, water, medical, comms, travel, internet,
            food, food, crime, crime, crime, comment, 1, 7078000
        ))
        conn.commit()


def insert_demo_message(callsign: str, group: str, message: str) -> None:
    """Insert a demo message.

    Args:
        callsign: Amateur callsign
        group: Group name
        message: Message content (ALL CAPS)
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    msg_id = random.randint(100, 999)

    with sqlite3.connect(DATABASE_FILE, timeout=10) as conn:
        conn.execute("""
            INSERT INTO messages_Data(datetime, groupid, idnum, callsign, message, frequency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, group, msg_id, callsign, message, 7078000))
        conn.commit()


def cleanup_demo_data() -> None:
    """Remove all demo-generated records from database."""
    with sqlite3.connect(DATABASE_FILE, timeout=10) as conn:
        conn.execute("DELETE FROM StatRep_Data WHERE SRid LIKE 'DEMO%'")
        conn.execute("DELETE FROM messages_Data WHERE message IN ({})".format(
            ",".join("?" * len(DEMO_MESSAGES))
        ), DEMO_MESSAGES)
        conn.commit()


class DemoRunner:
    """Runs the demo mode sequence over 60 seconds."""

    def __init__(self, main_window):
        """Initialize demo runner.

        Args:
            main_window: Reference to MainWindow for UI refresh
        """
        self.window = main_window
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.elapsed = 0  # seconds elapsed
        self.statrep_count = 0
        self.message_count = 0
        self.message_index = 0

    def start(self) -> None:
        """Start the demo sequence."""
        print("Demo mode starting...")
        cleanup_demo_data()  # Clear any previous demo data
        self.timer.start(2000)  # tick every 2 seconds
        self._tick()  # initial tick

    def _tick(self) -> None:
        """Called every 2 seconds during demo."""
        self.elapsed += 2

        if self.elapsed <= 10:
            # Phase 1 (0-10s): 5 green statreps in central
            self._add_statreps_central(1)
        elif self.elapsed <= 20:
            # Phase 2 (10-20s): 10 statreps, west coast red + 1 message
            self._add_statreps_coastal_west(2)
            if self.elapsed == 20 and self.message_count < 1:
                self._add_message()
        elif self.elapsed <= 30:
            # Phase 3 (20-30s): 20 statreps, northeast red + 2 messages
            self._add_statreps_coastal_west(1)
            self._add_statreps_coastal_northeast(3)
            if self.elapsed in [24, 30] and self.message_count < 3:
                self._add_message()
        elif self.elapsed <= 40:
            # Phase 4 (30-40s): 25 statreps, inland yellow + 3 messages
            self._add_statreps_coastal_west(1)
            self._add_statreps_coastal_northeast(1)
            self._add_statreps_inland(3)
            if self.elapsed in [32, 36, 40] and self.message_count < 6:
                self._add_message()
        elif self.elapsed <= 50:
            # Phase 5 (40-50s): 25 statreps, mixed everywhere + 2 messages
            self._add_statreps_coastal_west(2)
            self._add_statreps_coastal_northeast(2)
            self._add_statreps_inland(1)
            if self.elapsed in [44, 50] and self.message_count < 8:
                self._add_message()
        elif self.elapsed <= 60:
            # Phase 6 (50-60s): 15 statreps continued + 2 messages
            self._add_statreps_coastal_west(1)
            self._add_statreps_coastal_northeast(1)
            self._add_statreps_inland(1)
            if self.elapsed in [54, 60] and self.message_count < 10:
                self._add_message()
        else:
            # Demo complete
            self.timer.stop()
            print(f"Demo complete: {self.statrep_count} statreps, {self.message_count} messages")
            return

        # Refresh UI
        self.window._load_statrep_data()
        self.window._load_message_data()
        self.window._save_map_position(callback=self.window._load_map)

    def _add_statreps_central(self, count: int) -> None:
        """Add green statreps to central US."""
        for _ in range(count):
            grid = random.choice(CENTRAL_GRIDS)
            callsign = random.choice(CALLSIGNS)
            group = random.choice(GROUPS)
            insert_demo_statrep(callsign, grid, group, zone="central")
            self.statrep_count += 1

    def _add_statreps_coastal_west(self, count: int) -> None:
        """Add red statreps to west coast."""
        for _ in range(count):
            grid = random.choice(COASTAL_WEST_GRIDS)
            callsign = random.choice(CALLSIGNS)
            group = random.choice(GROUPS)
            insert_demo_statrep(callsign, grid, group, zone="coastal")
            self.statrep_count += 1

    def _add_statreps_coastal_northeast(self, count: int) -> None:
        """Add red statreps to northeast coast."""
        for _ in range(count):
            grid = random.choice(COASTAL_NORTHEAST_GRIDS)
            callsign = random.choice(CALLSIGNS)
            group = random.choice(GROUPS)
            insert_demo_statrep(callsign, grid, group, zone="coastal")
            self.statrep_count += 1

    def _add_statreps_inland(self, count: int) -> None:
        """Add yellow/mixed statreps to inland areas."""
        for _ in range(count):
            # Mix of west and northeast inland
            if random.random() < 0.5:
                grid = random.choice(INLAND_WEST_GRIDS)
            else:
                grid = random.choice(INLAND_NORTHEAST_GRIDS)
            callsign = random.choice(CALLSIGNS)
            group = random.choice(GROUPS)
            insert_demo_statrep(callsign, grid, group, zone="inland")
            self.statrep_count += 1

    def _add_message(self) -> None:
        """Add next demo message."""
        if self.message_index < len(DEMO_MESSAGES):
            callsign = random.choice(CALLSIGNS)
            group = random.choice(GROUPS)
            message = DEMO_MESSAGES[self.message_index]
            insert_demo_message(callsign, group, message)
            self.message_count += 1
            self.message_index += 1
