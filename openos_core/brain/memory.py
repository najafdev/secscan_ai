"""
OpenOS Personalized Memory System.

SQLite-backed persistent memory that tracks user habits, frequently used apps,
daily routines, and file access patterns. This data is injected into LLM prompts
to provide personalized, context-aware responses.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from openos_core.config import OPENOS_MEMORY_DB


class MemoryStore:
    """
    Persistent memory store for OpenOS personalization.

    Tracks:
    - App usage frequency and timing
    - Command history patterns
    - File access patterns
    - User-defined routines
    - Preferences learned from interactions
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or OPENOS_MEMORY_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS app_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                launched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hour_of_day INTEGER,
                day_of_week INTEGER
            );

            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT NOT NULL,
                resolved_action TEXT,
                success BOOLEAN DEFAULT 1,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS file_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                access_type TEXT DEFAULT 'open',
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                actions TEXT NOT NULL,  -- JSON array of actions
                trigger_time TEXT,      -- HH:MM format
                trigger_days TEXT,      -- JSON array of day numbers (0=Mon)
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_app_usage_name ON app_usage(app_name);
            CREATE INDEX IF NOT EXISTS idx_app_usage_hour ON app_usage(hour_of_day);
            CREATE INDEX IF NOT EXISTS idx_command_history_input ON command_history(user_input);
        """)
        conn.commit()

    # ── App Usage Tracking ──

    def record_app_launch(self, app_name: str) -> None:
        """Record that an application was launched."""
        now = datetime.now()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO app_usage (app_name, hour_of_day, day_of_week) VALUES (?, ?, ?)",
            (app_name.lower(), now.hour, now.weekday()),
        )
        conn.commit()

    def get_frequent_apps(self, limit: int = 10) -> list[dict]:
        """Get the most frequently used applications."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT app_name, COUNT(*) as count,
                   GROUP_CONCAT(DISTINCT hour_of_day) as usual_hours
            FROM app_usage
            WHERE launched_at > datetime('now', '-30 days')
            GROUP BY app_name
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_apps_for_time(self, hour: Optional[int] = None) -> list[str]:
        """Get apps the user typically uses at a given hour."""
        if hour is None:
            hour = datetime.now().hour
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT app_name, COUNT(*) as count
            FROM app_usage
            WHERE hour_of_day = ? AND launched_at > datetime('now', '-30 days')
            GROUP BY app_name
            ORDER BY count DESC
            LIMIT 5
            """,
            (hour,),
        ).fetchall()
        return [row["app_name"] for row in rows]

    # ── Command History ──

    def record_command(self, user_input: str, resolved_action: str, success: bool = True) -> None:
        """Record a command that was executed."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO command_history (user_input, resolved_action, success) VALUES (?, ?, ?)",
            (user_input, resolved_action, success),
        )
        conn.commit()

    def get_similar_commands(self, query: str, limit: int = 5) -> list[dict]:
        """Find similar past commands (simple LIKE matching)."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT user_input, resolved_action, success
            FROM command_history
            WHERE user_input LIKE ? AND success = 1
            ORDER BY executed_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Routines ──

    def save_routine(
        self,
        name: str,
        actions: list[str],
        description: str = "",
        trigger_time: Optional[str] = None,
        trigger_days: Optional[list[int]] = None,
    ) -> None:
        """Save or update a named routine."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO routines (name, description, actions, trigger_time, trigger_days)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name.lower(),
                description,
                json.dumps(actions),
                trigger_time,
                json.dumps(trigger_days) if trigger_days else None,
            ),
        )
        conn.commit()

    def get_routine(self, name: str) -> Optional[dict]:
        """Get a routine by name."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM routines WHERE name = ? AND enabled = 1",
            (name.lower(),),
        ).fetchone()
        if row:
            result = dict(row)
            result["actions"] = json.loads(result["actions"])
            if result["trigger_days"]:
                result["trigger_days"] = json.loads(result["trigger_days"])
            return result
        return None

    def get_current_routine(self) -> Optional[str]:
        """Get the routine summary for the current time/day."""
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        day = now.weekday()

        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT name, description, actions
            FROM routines
            WHERE enabled = 1 AND trigger_time IS NOT NULL
            """,
        ).fetchall()

        matching = []
        for row in rows:
            trigger_days = json.loads(row["trigger_days"]) if row["trigger_days"] else list(range(7))
            if day in trigger_days:
                # Check if within 30 minutes of trigger time
                trigger_h, trigger_m = map(int, row["trigger_time"].split(":"))
                trigger_minutes = trigger_h * 60 + trigger_m
                current_minutes = now.hour * 60 + now.minute
                if abs(current_minutes - trigger_minutes) <= 30:
                    actions = json.loads(row["actions"])
                    matching.append(f"- {row['name']}: {', '.join(actions)}")

        if matching:
            return "\n".join(matching)
        return None

    # ── Preferences ──

    def set_preference(self, key: str, value: str) -> None:
        """Set a user preference."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value),
        )
        conn.commit()

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    # ── Context Generation ──

    def get_context_summary(self) -> str:
        """Generate a context summary for LLM prompt injection."""
        parts = []

        # Frequent apps
        apps = self.get_frequent_apps(5)
        if apps:
            app_list = ", ".join(a["app_name"] for a in apps)
            parts.append(f"Frequently used apps: {app_list}")

        # Current time apps
        time_apps = self.get_apps_for_time()
        if time_apps:
            parts.append(f"Apps usually used around now: {', '.join(time_apps)}")

        # Recent commands
        conn = self._get_conn()
        recent = conn.execute(
            """
            SELECT user_input FROM command_history
            WHERE executed_at > datetime('now', '-1 day') AND success = 1
            ORDER BY executed_at DESC LIMIT 5
            """,
        ).fetchall()
        if recent:
            cmds = ", ".join(f'"{r["user_input"]}"' for r in recent)
            parts.append(f"Recent requests: {cmds}")

        return "\n".join(parts) if parts else ""

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
