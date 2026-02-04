"""
TommyTalker Session Database
SQLite database for session metadata storage.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
import uuid

from utils.config import get_sqlite_path


@dataclass
class Session:
    """A recording session."""
    id: str
    created_at: datetime
    mode: str
    duration_seconds: int
    audio_path: Optional[str]
    transcript_path: Optional[str]
    speaker_count: int = 1


class SessionDatabase:
    """
    SQLite database for storing session metadata.
    
    Stores information about recordings, transcripts, and modes used.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_sqlite_path()
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize()
        
    def _initialize(self):
        """Initialize the database and create tables."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        
        # Create sessions table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mode TEXT CHECK(mode IN ('cursor', 'editor', 'scribe', 'hud')),
                duration_seconds INTEGER,
                audio_path TEXT,
                transcript_path TEXT,
                speaker_count INTEGER DEFAULT 1
            )
        """)
        
        # Create transcripts table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER
            )
        """)
        
        self._connection.commit()
        print(f"[SessionDB] Initialized at: {self.db_path}")
        
    def create_session(self, mode: str, duration: int = 0, 
                       audio_path: Optional[str] = None) -> str:
        """
        Create a new session record.
        
        Args:
            mode: Operating mode (cursor, editor, scribe, hud)
            duration: Recording duration in seconds
            audio_path: Path to audio file
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        self._connection.execute(
            """
            INSERT INTO sessions (id, mode, duration_seconds, audio_path)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, mode, duration, audio_path)
        )
        self._connection.commit()
        
        print(f"[SessionDB] Created session: {session_id[:8]}... ({mode})")
        return session_id
        
    def update_session(self, session_id: str, **kwargs):
        """Update session fields."""
        allowed_fields = ['duration_seconds', 'audio_path', 'transcript_path', 'speaker_count']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return
            
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [session_id]
        
        self._connection.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",
            values
        )
        self._connection.commit()
        
    def add_transcript(self, session_id: str, content: str) -> str:
        """
        Add a transcript for a session.
        
        Args:
            session_id: Session ID
            content: Transcript text
            
        Returns:
            Transcript ID
        """
        transcript_id = str(uuid.uuid4())
        word_count = len(content.split())
        
        self._connection.execute(
            """
            INSERT INTO transcripts (id, session_id, content, word_count)
            VALUES (?, ?, ?, ?)
            """,
            (transcript_id, session_id, content, word_count)
        )
        self._connection.commit()
        
        return transcript_id
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        row = self._connection.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        
        if not row:
            return None
            
        return Session(
            id=row['id'],
            created_at=datetime.fromisoformat(row['created_at']),
            mode=row['mode'],
            duration_seconds=row['duration_seconds'] or 0,
            audio_path=row['audio_path'],
            transcript_path=row['transcript_path'],
            speaker_count=row['speaker_count'] or 1
        )
        
    def get_recent_sessions(self, limit: int = 10) -> List[Session]:
        """Get recent sessions ordered by creation date."""
        rows = self._connection.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        
        return [
            Session(
                id=row['id'],
                created_at=datetime.fromisoformat(row['created_at']),
                mode=row['mode'],
                duration_seconds=row['duration_seconds'] or 0,
                audio_path=row['audio_path'],
                transcript_path=row['transcript_path'],
                speaker_count=row['speaker_count'] or 1
            )
            for row in rows
        ]
        
    def get_session_count(self) -> int:
        """Get total number of sessions."""
        row = self._connection.execute("SELECT COUNT(*) FROM sessions").fetchone()
        return row[0]
        
    def delete_session(self, session_id: str):
        """Delete a session and its transcripts."""
        self._connection.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
        self._connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._connection.commit()
        
    def clear_all(self):
        """Clear all sessions and transcripts."""
        self._connection.execute("DELETE FROM transcripts")
        self._connection.execute("DELETE FROM sessions")
        self._connection.commit()
        print("[SessionDB] All sessions cleared")
        
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Global instance
_session_db: Optional[SessionDatabase] = None


def get_session_db() -> SessionDatabase:
    """Get the global session database instance."""
    global _session_db
    if _session_db is None:
        _session_db = SessionDatabase()
    return _session_db
