"""
TommyTalker Transcription History
SQLite database for storing and searching past transcriptions.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from utils.config import get_data_path


@dataclass
class HistoryEntry:
    """A single transcription history entry."""
    id: int
    timestamp: datetime
    mode: str  # cursor, editor, meeting, hud
    duration_seconds: float
    raw_text: str
    refined_text: Optional[str] = None
    audio_path: Optional[str] = None


class TranscriptionHistory:
    """
    SQLite-based transcription history storage.
    
    Stores all transcriptions with metadata for searching and export.
    """
    
    def __init__(self):
        self._db_path = get_data_path() / "history.db"
        self._init_database()
        
    def _init_database(self):
        """Initialize the database schema."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    duration_seconds REAL,
                    raw_text TEXT NOT NULL,
                    refined_text TEXT,
                    audio_path TEXT
                )
            """)
            
            # Create index for searching
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON transcriptions(timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mode 
                ON transcriptions(mode)
            """)
            
            conn.commit()
            
    def add(
        self,
        raw_text: str,
        mode: str,
        duration_seconds: float = 0,
        refined_text: Optional[str] = None,
        audio_path: Optional[str] = None
    ) -> int:
        """
        Add a new transcription to history.
        
        Returns:
            The ID of the new entry.
        """
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO transcriptions 
                (timestamp, mode, duration_seconds, raw_text, refined_text, audio_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, mode, duration_seconds, raw_text, refined_text, audio_path))
            
            conn.commit()
            return cursor.lastrowid
            
    def get_recent(self, limit: int = 50) -> list[HistoryEntry]:
        """Get the most recent transcriptions."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM transcriptions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
        return [self._row_to_entry(row) for row in rows]
        
    def search(self, query: str, limit: int = 50) -> list[HistoryEntry]:
        """Search transcriptions by text content."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM transcriptions
                WHERE raw_text LIKE ? OR refined_text LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
            
        return [self._row_to_entry(row) for row in rows]
        
    def get_by_mode(self, mode: str, limit: int = 50) -> list[HistoryEntry]:
        """Get transcriptions filtered by mode."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM transcriptions
                WHERE mode = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (mode, limit)).fetchall()
            
        return [self._row_to_entry(row) for row in rows]
        
    def get_by_id(self, entry_id: int) -> Optional[HistoryEntry]:
        """Get a specific transcription by ID."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM transcriptions WHERE id = ?
            """, (entry_id,)).fetchone()
            
        return self._row_to_entry(row) if row else None
        
    def delete(self, entry_id: int) -> bool:
        """Delete a transcription by ID."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM transcriptions WHERE id = ?
            """, (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
            
    def clear_all(self):
        """Clear all history entries."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM transcriptions")
            conn.commit()
            
    def count(self) -> int:
        """Get total number of transcriptions."""
        with sqlite3.connect(self._db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
            
    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Convert a database row to a HistoryEntry."""
        return HistoryEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            mode=row["mode"],
            duration_seconds=row["duration_seconds"] or 0,
            raw_text=row["raw_text"],
            refined_text=row["refined_text"],
            audio_path=row["audio_path"]
        )


# Global instance
_history: TranscriptionHistory | None = None


def get_history() -> TranscriptionHistory:
    """Get the global history instance."""
    global _history
    if _history is None:
        _history = TranscriptionHistory()
    return _history
