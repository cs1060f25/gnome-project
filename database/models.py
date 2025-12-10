"""
Database models for Gnome file tracking and embeddings storage.
Includes support for storing vector embeddings alongside file metadata.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import hashlib
import json


class GnomeDatabase:
    """Main database interface for Gnome with embeddings support."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        if db_path is None:
            # Default to user's app data directory
            app_data = Path.home() / '.gnome'
            app_data.mkdir(exist_ok=True)
            db_path = str(app_data / 'gnome.db')
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()
    
    def init_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Files table with embedding support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                source TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                vector_id TEXT,
                file_size INTEGER,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        # Embeddings table - stores vector embeddings for semantic search
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                vector_id TEXT UNIQUE NOT NULL,
                embedding_vector BLOB NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        # Sync state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_state (
                source TEXT PRIMARY KEY,
                last_sync TIMESTAMP,
                status TEXT,
                cursor TEXT,
                enabled BOOLEAN DEFAULT 1,
                error_message TEXT
            )
        ''')
        
        # OAuth tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                service TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Watched folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watched_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                recursive BOOLEAN DEFAULT 1,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_source ON files(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_vector_id ON files(vector_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_file_id ON embeddings(file_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_vector_id ON embeddings(vector_id)')
        
        self.conn.commit()
    
    # File operations
    def add_file(self, filename: str, file_path: str, source: str, 
                 file_hash: str, vector_id: str = None, file_size: int = None,
                 metadata: dict = None) -> int:
        """Add a new file to the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO files (filename, file_path, source, file_hash, vector_id, 
                             file_size, last_modified, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, source, file_hash, vector_id, 
              file_size, datetime.now().isoformat(),
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_file_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Check if file already exists by hash."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM files WHERE file_hash = ? AND is_deleted = 0', 
                      (file_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_files_by_source(self, source: str) -> List[Dict]:
        """Get all files from a specific source."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM files 
            WHERE source = ? AND is_deleted = 0 
            ORDER BY last_modified DESC
        ''', (source,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_files(self) -> List[Dict]:
        """Get all active files."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM files 
            WHERE is_deleted = 0 
            ORDER BY last_modified DESC
        ''')
        files = []
        for row in cursor.fetchall():
            file_dict = dict(row)
            # Parse metadata JSON if present
            if file_dict.get('metadata'):
                try:
                    file_dict['metadata'] = json.loads(file_dict['metadata'])
                except:
                    file_dict['metadata'] = {}
            files.append(file_dict)
        return files
    
    def mark_file_deleted(self, file_id: int):
        """Mark a file as deleted (soft delete)."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE files SET is_deleted = 1 WHERE id = ?', (file_id,))
        self.conn.commit()
    
    # Embedding operations (FIX for BUG CS1060-151)
    def store_embedding(self, file_id: int, vector_id: str, embedding: List[float]) -> int:
        """
        Store an embedding vector for a file.
        
        Args:
            file_id: ID of the file
            vector_id: Unique identifier for the vector
            embedding: List of floats representing the vector
        
        Returns:
            ID of the stored embedding
        """
        if not embedding or not isinstance(embedding, (list, tuple)):
            raise ValueError("Embedding must be a non-empty list or tuple of floats")
        
        # Convert embedding list to bytes for storage
        import array
        embedding_bytes = array.array('f', embedding).tobytes()
        dimension = len(embedding)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO embeddings (file_id, vector_id, embedding_vector, dimension)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(vector_id) DO UPDATE SET
                embedding_vector = excluded.embedding_vector,
                dimension = excluded.dimension
        ''', (file_id, vector_id, embedding_bytes, dimension))
        
        # Update file record with vector_id
        cursor.execute('''
            UPDATE files SET vector_id = ? WHERE id = ?
        ''', (vector_id, file_id))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_embedding(self, vector_id: str) -> Optional[List[float]]:
        """
        Retrieve an embedding vector by its ID.
        
        Args:
            vector_id: Unique identifier for the vector
        
        Returns:
            List of floats or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT embedding_vector, dimension 
            FROM embeddings 
            WHERE vector_id = ?
        ''', (vector_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Convert bytes back to list of floats
        import array
        embedding_bytes = row[0]
        dimension = row[1]
        
        # Reconstruct the array
        embedding = array.array('f')
        embedding.frombytes(embedding_bytes)
        return list(embedding)
    
    def get_all_embeddings(self) -> List[Dict]:
        """Get all embeddings with their associated file information."""
        import array
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.id, e.file_id, e.vector_id, e.embedding_vector, e.dimension, e.created_at,
                   f.filename, f.file_path, f.source
            FROM embeddings e
            JOIN files f ON e.file_id = f.id
            WHERE f.is_deleted = 0
            ORDER BY e.created_at DESC
        ''')
        
        embeddings = []
        for row in cursor.fetchall():
            # Convert bytes to list
            embedding_bytes = row[3]
            embedding_array = array.array('f')
            embedding_array.frombytes(embedding_bytes)
            
            embeddings.append({
                'id': row[0],
                'file_id': row[1],
                'vector_id': row[2],
                'embedding': list(embedding_array),
                'dimension': row[4],
                'created_at': row[5],
                'filename': row[6],
                'file_path': row[7],
                'source': row[8]
            })
        
        return embeddings
    
    # Sync state operations
    def update_sync_state(self, source: str, status: str, cursor_value: str = None, 
                         error: str = None):
        """Update sync state for a source."""
        cursor_obj = self.conn.cursor()
        cursor_obj.execute('''
            INSERT INTO sync_state (source, last_sync, status, cursor, error_message)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_sync = excluded.last_sync,
                status = excluded.status,
                cursor = excluded.cursor,
                error_message = excluded.error_message
        ''', (source, datetime.now().isoformat(), status, cursor_value, error))
        self.conn.commit()
    
    def get_sync_state(self, source: str) -> Optional[Dict]:
        """Get sync state for a source."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sync_state WHERE source = ?', (source,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # OAuth token operations
    def save_oauth_token(self, service: str, access_token: str, 
                        refresh_token: str = None, expires_at: str = None):
        """Save OAuth tokens for a service."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO oauth_tokens (service, access_token, refresh_token, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(service) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
        ''', (service, access_token, refresh_token, expires_at, 
              datetime.now().isoformat()))
        self.conn.commit()
    
    def get_oauth_token(self, service: str) -> Optional[Dict]:
        """Get OAuth token for a service."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM oauth_tokens WHERE service = ?', (service,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_oauth_token(self, service: str):
        """Delete OAuth token (disconnect service)."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM oauth_tokens WHERE service = ?', (service,))
        self.conn.commit()
    
    # Watched folders operations
    def add_watched_folder(self, source: str, folder_path: str, recursive: bool = True):
        """Add a folder to watch list."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO watched_folders (source, folder_path, recursive)
            VALUES (?, ?, ?)
        ''', (source, folder_path, recursive))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_watched_folders(self, source: str) -> List[Dict]:
        """Get all watched folders for a source."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM watched_folders 
            WHERE source = ? AND enabled = 1
        ''', (source,))
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

