"""
Database layer for WhatsApp Cross-Platform Price Sync.
Optimized for ultra-low storage footprint, automated pruning,
and Meta Facebook Developer Account credentials persistence.
"""

import os
import sqlite3
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

DB_PATH = Path(__file__).parent / "shop_bridge.db"
MAX_MESSAGE_RETENTION = 50  # Keep DB ultra-compact (< 100 KB)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high performance and low storage overhead
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA auto_vacuum = INCREMENTAL;")
    return conn


def init_db():
    """Initializes tables, sets retention policies, and seeds defaults."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                allow_all INTEGER DEFAULT 1,
                last_query TEXT,
                last_query_time REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Compact Messages table with auto-indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                query TEXT,
                source_site TEXT,
                whatsapp_text TEXT,
                delivery_status TEXT,
                winner_platform TEXT,
                lowest_price TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: ensure new columns exist if table was already created
        cursor.execute("PRAGMA table_info(messages);")
        existing_cols = [col["name"] for col in cursor.fetchall()]
        if "winner_platform" not in existing_cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN winner_platform TEXT;")
        if "lowest_price" not in existing_cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN lowest_price TEXT;")

        # 3. Meta Facebook / WhatsApp Business App Config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure demo user exists
        cursor.execute("SELECT phone FROM users WHERE phone = ?", ("919876543210",))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (phone, allow_all, last_query, last_query_time) VALUES (?, 1, NULL, 0)",
                ("919876543210",)
            )

        conn.commit()


def save_meta_config(token: str, phone_number_id: str, waba_id: str = "", target_phone: str = ""):
    """Stores Meta Facebook Developer Account WhatsApp credentials."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO meta_config (key, value) VALUES ('whatsapp_token', ?)", (token.strip(),))
        cursor.execute("INSERT OR REPLACE INTO meta_config (key, value) VALUES ('phone_number_id', ?)", (phone_number_id.strip(),))
        cursor.execute("INSERT OR REPLACE INTO meta_config (key, value) VALUES ('waba_id', ?)", (waba_id.strip(),))
        if target_phone:
            clean_target = "".join(filter(str.isdigit, str(target_phone)))
            cursor.execute("INSERT OR REPLACE INTO meta_config (key, value) VALUES ('target_phone', ?)", (clean_target,))
        conn.commit()


def get_meta_config() -> Dict[str, str]:
    """Retrieves saved Meta Developer credentials."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM meta_config")
        rows = cursor.fetchall()
        config = {row["key"]: row["value"] for row in rows}
        return {
            "whatsapp_token": config.get("whatsapp_token", ""),
            "phone_number_id": config.get("phone_number_id", ""),
            "waba_id": config.get("waba_id", ""),
            "target_phone": config.get("target_phone", "919876543210")
        }


def upsert_user(phone: str, allow_all: bool = True) -> Dict:
    """Creates or updates a user's allow_all preference."""
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    if not clean_phone:
        clean_phone = "919876543210"

    allow_val = 1 if allow_all else 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (phone, allow_all, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone) DO UPDATE SET
                allow_all = excluded.allow_all,
                updated_at = CURRENT_TIMESTAMP
        """, (clean_phone, allow_val))
        conn.commit()
    return get_user(clean_phone)


def get_user(phone: str) -> Optional[Dict]:
    """Retrieves user profile by phone."""
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (clean_phone,))
        row = cursor.fetchone()
        if row:
            return {
                "phone": row["phone"],
                "allow_all": bool(row["allow_all"]),
                "last_query": row["last_query"],
                "last_query_time": row["last_query_time"],
                "updated_at": row["updated_at"]
            }
        return None


def get_all_users() -> List[Dict]:
    """Retrieves all registered users."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [
            {
                "phone": row["phone"],
                "allow_all": bool(row["allow_all"]),
                "last_query": row["last_query"],
                "last_query_time": row["last_query_time"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


def is_duplicate_recent(phone: str, query: str, cooldown_seconds: int = 60) -> bool:
    """
    Checks if the exact same query was submitted by this phone
    within the cooldown window (default 60 seconds).
    """
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    clean_query = query.strip().lower()
    now = time.time()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_query, last_query_time FROM users WHERE phone = ?",
            (clean_phone,)
        )
        row = cursor.fetchone()
        if row and row["last_query"]:
            last_q = (row["last_query"] or "").strip().lower()
            last_time = row["last_query_time"] or 0
            if last_q == clean_query and (now - last_time) < cooldown_seconds:
                return True

    return False


def update_user_search(phone: str, query: str):
    """Updates the last query and timestamp for deduplication."""
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    now = time.time()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET last_query = ?, last_query_time = ?, updated_at = CURRENT_TIMESTAMP
            WHERE phone = ?
        """, (query.strip(), now, clean_phone))
        conn.commit()


def save_message(
    phone: str,
    query: str,
    source_site: str,
    whatsapp_text: str,
    delivery_status: str,
    winner_platform: str = "",
    lowest_price: str = ""
) -> int:
    """
    Stores a dispatched WhatsApp comparison with automatic pruning
    to guarantee ultra-low storage usage (< 100 KB).
    """
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (
                phone, query, source_site, whatsapp_text, delivery_status,
                winner_platform, lowest_price, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (clean_phone, query, source_site, whatsapp_text, delivery_status, winner_platform, lowest_price))
        msg_id = cursor.lastrowid

        # Auto-prune: Keep only MAX_MESSAGE_RETENTION latest rows
        cursor.execute("""
            DELETE FROM messages
            WHERE id NOT IN (
                SELECT id FROM messages ORDER BY id DESC LIMIT ?
            )
        """, (MAX_MESSAGE_RETENTION,))

        conn.commit()

        # Incremental vacuum to reclaim space immediately
        cursor.execute("PRAGMA incremental_vacuum;")
        return msg_id


def get_recent_messages(limit: int = 20) -> List[Dict]:
    """Retrieves the latest messages logged for display."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, phone, query, source_site, whatsapp_text, delivery_status,
                   winner_platform, lowest_price, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        results = [
            {
                "id": row["id"],
                "phone": row["phone"],
                "query": row["query"],
                "source_site": row["source_site"],
                "whatsapp_text": row["whatsapp_text"],
                "delivery_status": row["delivery_status"],
                "winner_platform": row["winner_platform"],
                "lowest_price": row["lowest_price"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
        results.reverse()
        return results


def get_storage_stats() -> Dict[str, Any]:
    """
    Computes exact storage metrics for transparency and validation
    showing that messages occupy minimal disk footprint.
    """
    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    wal_path = Path(str(DB_PATH) + "-wal")
    wal_size_bytes = wal_path.stat().st_size if wal_path.exists() else 0
    total_disk_bytes = db_size_bytes + wal_size_bytes

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM messages")
        msg_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM users")
        user_count = cursor.fetchone()["count"]

    avg_bytes_per_msg = int(total_disk_bytes / max(msg_count, 1))

    # Human-readable format
    if total_disk_bytes < 1024 * 1024:
        formatted_size = f"{total_disk_bytes / 1024:.1f} KB"
        status_label = "🟢 Ultra-Lightweight (<1 MB)"
    else:
        formatted_size = f"{total_disk_bytes / (1024 * 1024):.2f} MB"
        status_label = "🟡 Moderate"

    return {
        "db_size_bytes": total_disk_bytes,
        "db_size_formatted": formatted_size,
        "message_count": msg_count,
        "user_count": user_count,
        "avg_bytes_per_message": f"~{avg_bytes_per_msg} bytes",
        "retention_limit": MAX_MESSAGE_RETENTION,
        "storage_status": status_label,
        "auto_pruning_active": True,
        "journal_mode": "WAL",
        "db_path": str(DB_PATH)
    }


def vacuum_database() -> Dict[str, Any]:
    """Manually runs SQLite VACUUM to shrink the database file to its minimum possible size."""
    with get_connection() as conn:
        conn.execute("VACUUM;")
    return get_storage_stats()


def clear_message_history() -> Dict[str, Any]:
    """Purges all stored comparison messages and reclaims disk space."""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages;")
        conn.execute("VACUUM;")
    return get_storage_stats()
