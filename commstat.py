#!/usr/bin/env python3
# Copyright (c) 2025 Manuel Ochoa
# This file is part of CommStat.
# Licensed under the GNU General Public License v3.0.
"""
commstat.py - CommStat Launcher

Checks for pending updates before launching the main application.
If an update zip file is present, asks the user before extracting it to overwrite program files.
"""

import os
import sys
import sqlite3
import zipfile
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Constants
SCRIPT_DIR = Path(__file__).parent.resolve()
UPDATE_FOLDER = SCRIPT_DIR / "updates"
UPDATE_ZIP = UPDATE_FOLDER / "update.zip"
MAIN_APP = SCRIPT_DIR / "little_gucci.py"
DATABASE_FILE = SCRIPT_DIR / "traffic.db3"
DATABASE_TEMPLATE = SCRIPT_DIR / "traffic.db3.template"
DATABASE_JOURNAL = SCRIPT_DIR / "traffic.db3-journal"
DATABASE_WAL = SCRIPT_DIR / "traffic.db3-wal"


def apply_update() -> bool:
    """
    Check for and apply pending update.

    Returns:
        True if update was applied, False otherwise.
    """
    if not UPDATE_ZIP.exists():
        return False

    # Ask user before applying
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(
        "Update Available",
        "A CommStat update is available. Would you like to install it now?"
    )
    root.update()
    root.destroy()

    if not answer:
        print("Update skipped by user.")
        return False

    print("Applying update...")

    try:
        with zipfile.ZipFile(UPDATE_ZIP, 'r') as zf:
            file_list = zf.namelist()
            print(f"Updating {len(file_list)} files...")
            zf.extractall(SCRIPT_DIR)

        UPDATE_ZIP.unlink()
        print("Update applied successfully.")

        if UPDATE_FOLDER.exists() and not any(UPDATE_FOLDER.iterdir()):
            UPDATE_FOLDER.rmdir()

        return True

    except zipfile.BadZipFile:
        print(f"Error: {UPDATE_ZIP} is not a valid zip file.")
        bad_zip = UPDATE_FOLDER / "update_bad.zip"
        UPDATE_ZIP.rename(bad_zip)
        return False

    except PermissionError as e:
        print(f"Error: Permission denied - {e}")
        return False

    except Exception as e:
        print(f"Error applying update: {e}")
        return False


def setup_database() -> bool:
    """
    Ensure the database file exists, copying from template if needed.

    Returns:
        True if database was created from template, False if it already existed.
    """
    if DATABASE_FILE.exists():
        return False

    if DATABASE_TEMPLATE.exists():
        shutil.copy(DATABASE_TEMPLATE, DATABASE_FILE)
        print(f"Created {DATABASE_FILE.name} from template")
        return True
    else:
        print(f"Warning: {DATABASE_TEMPLATE.name} not found, cannot create {DATABASE_FILE.name}")
        return False


def check_database() -> None:
    """
    Run integrity check and lock detection on traffic.db3.

    Warns the user (via console + dialog) if any issues are found,
    and offers to abort the launch.
    """
    if not DATABASE_FILE.exists():
        return  # setup_database() already handled missing db

    warnings = []

    # Check for leftover journal/WAL files (unclean shutdown indicator)
    for stale in (DATABASE_JOURNAL, DATABASE_WAL):
        if stale.exists():
            warnings.append(f"Stale file found (unclean shutdown?): {stale.name}")

    # Integrity check + lock detection via Python sqlite3
    try:
        con = sqlite3.connect(str(DATABASE_FILE), timeout=1)
        result = con.execute("PRAGMA integrity_check;").fetchall()
        con.close()
        flat = [row[0] for row in result]
        if flat == ["ok"]:
            print(f"{DATABASE_FILE.name}: ok")
        else:
            for msg in flat:
                warnings.append(f"Integrity issue: {msg}")
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            warnings.append(f"{DATABASE_FILE.name} is locked — another instance may be running.")
        else:
            warnings.append(f"Database error: {e}")

    if not warnings:
        return

    for w in warnings:
        print(f"WARNING: {w}")

    msg = "\n".join(warnings) + "\n\nLaunch CommStat anyway?"
    root = tk.Tk()
    root.withdraw()
    proceed = messagebox.askyesno("Database Warning", msg, icon="warning")
    root.update()
    root.destroy()
    if not proceed:
        sys.exit(1)


def launch_main_app() -> None:
    """Launch the main CommStat application."""
    if not MAIN_APP.exists():
        print(f"Error: {MAIN_APP} not found.")
        sys.exit(1)

    env = os.environ.copy()
    if sys.platform.startswith('linux'):
        # Use qt5ct so the app follows the system theme on Linux.
        # Only set it if the user hasn't already configured a preference.
        if not env.get('QT_QPA_PLATFORMTHEME'):
            env['QT_QPA_PLATFORMTHEME'] = 'qt5ct'
        # Disable the Ubuntu/Unity global menu proxy that hijacks the menu bar.
        # These env vars are ignored on desktops that don't use the global menu
        # (KDE, XFCE, Cinnamon, etc.) so they are safe to set unconditionally.
        env['UBUNTU_MENUPROXY'] = ''
        env['QT_NO_UBUNTU_OVERLAY'] = '1'

    python = sys.executable
    args = [python, str(MAIN_APP)] + sys.argv[1:]  # Pass through any command line args
    subprocess.run(args, cwd=str(SCRIPT_DIR), env=env)


def main() -> None:
    """Main entry point."""
    if not UPDATE_FOLDER.exists():
        UPDATE_FOLDER.mkdir(parents=True, exist_ok=True)

    apply_update()
    setup_database()
    check_database()
    launch_main_app()


if __name__ == "__main__":
    main()
