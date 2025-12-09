"""
Test suite for database embedding storage - BUG CS1060-151
Tests that the database correctly stores and retrieves vector embeddings for files.

This test was generated to reproduce and validate the fix for:
BUG CS1060-151: Database setup fails to store embeddings during indexing

Expected behavior: Database should store embeddings as BLOB and retrieve them correctly
Actual behavior (before fix): Embeddings table missing, no store_embedding method
"""
import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import GnomeDatabase, compute_file_hash


class TestDatabaseEmbeddings(unittest.TestCase):
    """Test database embedding storage functionality"""
    
    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = GnomeDatabase(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Clean up temporary database"""
        self.db.close()
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_database_initialization(self):
        """Test that database and embeddings table are created"""
        # Check that embeddings table exists
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='embeddings'
        ''')
        result = cursor.fetchone()
        self.assertIsNotNone(result, "Embeddings table should exist")
    
    def test_store_embedding_basic(self):
        """Test storing a basic embedding vector"""
        # First, add a file
        file_id = self.db.add_file(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            source="Finder",
            file_hash="abc123",
            file_size=1000
        )
        
        # Create a simple embedding vector
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        vector_id = "test_vec_001"
        
        # Store the embedding - this should NOT raise an error
        try:
            emb_id = self.db.store_embedding(file_id, vector_id, embedding)
            self.assertIsNotNone(emb_id, "Embedding ID should be returned")
        except Exception as e:
            self.fail(f"store_embedding raised an exception: {e}")
    
    def test_store_and_retrieve_embedding(self):
        """Test storing and retrieving an embedding vector"""
        # Add a file
        file_id = self.db.add_file(
            filename="resume.pdf",
            file_path="/tmp/resume.pdf",
            source="Finder",
            file_hash="def456",
            file_size=2000
        )
        
        # Create an embedding (simulating a 1024-dim vector)
        embedding = [float(i) * 0.01 for i in range(1024)]
        vector_id = "resume_vec_001"
        
        # Store the embedding
        self.db.store_embedding(file_id, vector_id, embedding)
        
        # Retrieve the embedding
        retrieved = self.db.get_embedding(vector_id)
        
        self.assertIsNotNone(retrieved, "Should retrieve stored embedding")
        self.assertEqual(len(retrieved), 1024, "Should have 1024 dimensions")
        
        # Check values are approximately correct (floating point precision)
        for i in range(10):  # Check first 10 values
            self.assertAlmostEqual(retrieved[i], embedding[i], places=5)
    
    def test_store_embedding_updates_file(self):
        """Test that storing embedding updates the file's vector_id"""
        # Add a file
        file_id = self.db.add_file(
            filename="document.docx",
            file_path="/tmp/document.docx",
            source="Google Drive",
            file_hash="xyz789",
            file_size=3000
        )
        
        # Store embedding
        embedding = [0.5] * 512
        vector_id = "doc_vec_001"
        self.db.store_embedding(file_id, vector_id, embedding)
        
        # Check that file record has vector_id
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT vector_id FROM files WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "File should exist")
        self.assertEqual(result[0], vector_id, "File should have vector_id set")
    
    def test_get_all_embeddings(self):
        """Test retrieving all embeddings"""
        # Add multiple files with embeddings
        for i in range(3):
            file_id = self.db.add_file(
                filename=f"file{i}.pdf",
                file_path=f"/tmp/file{i}.pdf",
                source="Finder",
                file_hash=f"hash{i}",
                file_size=1000 * (i + 1)
            )
            
            embedding = [float(i) * 0.1] * 256
            self.db.store_embedding(file_id, f"vec_{i}", embedding)
        
        # Retrieve all embeddings
        all_embeddings = self.db.get_all_embeddings()
        
        self.assertEqual(len(all_embeddings), 3, "Should have 3 embeddings")
        
        # Check structure
        for emb in all_embeddings:
            self.assertIn('id', emb)
            self.assertIn('file_id', emb)
            self.assertIn('vector_id', emb)
            self.assertIn('embedding', emb)
            self.assertIn('dimension', emb)
            self.assertIn('filename', emb)
    
    def test_store_empty_embedding_raises_error(self):
        """Test that storing empty embedding raises error"""
        file_id = self.db.add_file(
            filename="empty.txt",
            file_path="/tmp/empty.txt",
            source="Finder",
            file_hash="empty123",
            file_size=0
        )
        
        # Try to store empty embedding
        with self.assertRaises(ValueError):
            self.db.store_embedding(file_id, "empty_vec", [])
    
    def test_store_invalid_embedding_type(self):
        """Test that storing invalid type raises error"""
        file_id = self.db.add_file(
            filename="invalid.txt",
            file_path="/tmp/invalid.txt",
            source="Finder",
            file_hash="invalid123",
            file_size=100
        )
        
        # Try to store non-list embedding
        with self.assertRaises(ValueError):
            self.db.store_embedding(file_id, "invalid_vec", "not a list")
    
    def test_large_embedding_vector(self):
        """Test storing and retrieving large embedding (1536-dim like OpenAI)"""
        file_id = self.db.add_file(
            filename="large_doc.pdf",
            file_path="/tmp/large_doc.pdf",
            source="Finder",
            file_hash="large123",
            file_size=10000
        )
        
        # Create large embedding (1536 dimensions)
        embedding = [float(i) * 0.001 for i in range(1536)]
        vector_id = "large_vec_001"
        
        # Store and retrieve
        self.db.store_embedding(file_id, vector_id, embedding)
        retrieved = self.db.get_embedding(vector_id)
        
        self.assertEqual(len(retrieved), 1536, "Should preserve 1536 dimensions")
        
        # Check a few random values
        for i in [0, 100, 500, 1000, 1535]:
            self.assertAlmostEqual(retrieved[i], embedding[i], places=5)
    
    def test_embedding_persists_across_connections(self):
        """Test that embeddings persist when database is reopened"""
        # Add file and embedding
        file_id = self.db.add_file(
            filename="persist.pdf",
            file_path="/tmp/persist.pdf",
            source="Finder",
            file_hash="persist123",
            file_size=5000
        )
        
        embedding = [1.0, 2.0, 3.0, 4.0, 5.0]
        vector_id = "persist_vec"
        self.db.store_embedding(file_id, vector_id, embedding)
        
        # Close and reopen database
        self.db.close()
        self.db = GnomeDatabase(db_path=self.temp_db.name)
        
        # Retrieve embedding
        retrieved = self.db.get_embedding(vector_id)
        
        self.assertIsNotNone(retrieved, "Embedding should persist")
        self.assertEqual(len(retrieved), 5)
        for i in range(5):
            self.assertAlmostEqual(retrieved[i], embedding[i], places=5)


class TestFileHashComputation(unittest.TestCase):
    """Test file hash computation utility"""
    
    def test_compute_file_hash(self):
        """Test that file hash is computed correctly"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("Test content for hashing")
            temp_file = f.name
        
        try:
            # Compute hash
            file_hash = compute_file_hash(temp_file)
            
            # Hash should be a non-empty string
            self.assertIsInstance(file_hash, str)
            self.assertGreater(len(file_hash), 0)
            
            # Hash should be consistent
            hash2 = compute_file_hash(temp_file)
            self.assertEqual(file_hash, hash2)
            
        finally:
            os.unlink(temp_file)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 70)
    print("BUG CS1060-151: Test Database Embedding Storage")
    print("=" * 70)
    print()
    run_tests()


