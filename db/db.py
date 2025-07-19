import sqlite3
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = 'voice_channels.db'):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the necessary tables if they don't exist."""
        with self.conn:
            # Create parent_voices table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS parent_voices (
                    channel_id BIGINT PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    name_template TEXT NOT NULL
                )
            """)
            
            # Create temporary_voices table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS temporary_voices (
                    channel_id BIGINT PRIMARY KEY,
                    parent_voice_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    serial_number BIGINT NOT NULL CHECK (serial_number > 0),
                    FOREIGN KEY (parent_voice_id) REFERENCES parent_voices(channel_id)
                )
            """)
    
    def add_parent_voice(self, channel_id: int, guild_id: int, name_template: str) -> None:
        """Add a new parent voice channel to the database."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO parent_voices (channel_id, guild_id, name_template)
                VALUES (?, ?, ?)
            """, (channel_id, guild_id, name_template))
    
    def add_temporary_voice(self, channel_id: int, parent_voice_id: int, guild_id: int, serial_number: int) -> None:
        """Add a new temporary voice channel to the database."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO temporary_voices (channel_id, parent_voice_id, guild_id, serial_number)
                VALUES (?, ?, ?, ?)
            """, (channel_id, parent_voice_id, guild_id, serial_number))

    def update_parent_voice(self, channel_id: int, guild_id: int, name_template: str) -> None:
        """Update the name template of an existing parent voice channel."""
        with self.conn:
            self.conn.execute("""
                UPDATE parent_voices
                SET guild_id = ?, name_template = ?
                WHERE channel_id = ?
            """, (guild_id, name_template, channel_id))
    
    def update_temporary_voice(self, channel_id: int, parent_voice_id: int, guild_id: int, serial_number: int) -> None:
        """Update the parent_voice_id and serial_number of an existing temporary voice channel."""
        with self.conn:
            self.conn.execute("""
                UPDATE temporary_voices
                SET guild_id = ?, parent_voice_id = ?, serial_number = ?
                WHERE channel_id = ? AND guild_id = ?
            """, (guild_id, parent_voice_id, serial_number, channel_id))
    
    def delete_parent_voice(self, channel_id: int) -> None:
        """Delete a parent voice channel from the database."""
        with self.conn:
            self.conn.execute("""
                DELETE FROM parent_voices
                WHERE channel_id = ?
            """, (channel_id,))
    
    def delete_temporary_voice(self, channel_id: int) -> None:
        """Delete a temporary voice channel from the database."""
        with self.conn:
            self.conn.execute("""
                DELETE FROM temporary_voices
                WHERE channel_id = ?
            """, (channel_id,))
    
    def get_parent_voice(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get a parent voice channel by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT channel_id, guild_id, name_template
            FROM parent_voices
            WHERE channel_id = ?
        """, (channel_id,))
        row = cursor.fetchone()
        if row:
            return {
                'channel_id': row[0],
                'guild_id': row[1],
                'name_template': row[2]
            }
        return None
    
    def get_all_parent_voices_from_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all parent voice channels that are in a guild with specified ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT channel_id, guild_id, name_template
            FROM parent_voices
            WHERE guild_id = ?
        """, (guild_id,))
        rows = cursor.fetchall()
        result = [
            {
                'channel_id': row[0],
                'guild_id': row[1],
                'name_template': row[2]
            }
            for row in rows
        ]
        return result
    
    def get_temporary_voice(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get a temporary voice channel by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT channel_id, parent_voice_id, guild_id, serial_number
            FROM temporary_voices
            WHERE channel_id = ?
        """, (channel_id,))
        row = cursor.fetchone()
        if row:
            return {
                'channel_id': row[0],
                'parent_voice_id': row[1],
                'guild_id': row[2],
                'serial_number': row[3]
            }
        return None
    
    def get_next_serial_number(self, parent_voice_id: int) -> int:
        """
        Get the minimum excluded value (MEX) among serial numbers for a given parent voice.
        This is the smallest positive integer not currently used as a serial number.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT serial_number
            FROM temporary_voices
            WHERE parent_voice_id = ?
            ORDER BY serial_number
        """, (parent_voice_id,))
        
        serial_numbers = [row[0] for row in cursor.fetchall()]
        
        # If there are no temporary voices for this parent, start with 1
        if not serial_numbers:
            return 1
        
        # Find the first gap in the sequence starting from 1
        expected = 1
        for num in sorted(serial_numbers):
            if num == expected:
                expected += 1
            elif num > expected:
                # Found a gap, return the expected number
                return expected
        
        # If no gaps found, return the next number after the highest
        return expected
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the connection."""
        self.close()