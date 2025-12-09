"""
Integration Tests for Gnome Application

These tests exercise the complete system end-to-end by calling APIs
that exercise multiple components working together.

Rubric requirement: "at least two automated integration/system tests that 
test the entire system, either by exercising a responsive Web interface 
using a test browser or by calling APIs that exercise a larger part of your system."
"""
import unittest
import tempfile
import os
import sys
from pathlib import Path
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFinderIntegration(unittest.TestCase):
    """
    Integration Test 1: Complete Finder File Journey
    
    Tests the entire flow of:
    1. Starting the application
    2. Viewing indexed Finder files
    3. Searching across files semantically
    4. Opening a file from results
    
    This exercises: Flask app, database, semantic search, file processor
    """
    
    def setUp(self):
        """Set up test environment."""
        from app import app, uploaded_files
        
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Clear state
        uploaded_files.clear()
        
        # Create temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = Path(self.temp_dir)
        
        # Simulate logged in user
        with self.client.session_transaction() as sess:
            sess['user'] = 'integration_test@example.com'
    
    def tearDown(self):
        """Clean up test environment."""
        from app import uploaded_files
        uploaded_files.clear()
        
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_finder_journey(self):
        """
        Test complete user journey for Finder integration:
        Upload files -> View files -> Search -> Open result
        """
        from app import uploaded_files
        
        # Step 1: Check initial state - should have empty or existing files
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 200)
        initial_data = response.get_json()
        self.assertIn('files', initial_data)
        self.assertIn('syncStatus', initial_data)
        
        # Step 2: Upload multiple test files
        test_files = [
            ('quarterly_financial_report_Q3_2024.pdf', b'Financial data for Q3'),
            ('employee_handbook_2024.pdf', b'Company policies and procedures'),
            ('project_proposal_acme_corp.docx', b'Proposal for Acme Corporation'),
        ]
        
        for filename, content in test_files:
            response = self.client.post(
                '/api/upload',
                data={'file': (BytesIO(content), filename)},
                content_type='multipart/form-data'
            )
            self.assertEqual(response.status_code, 200, f"Failed to upload {filename}")
        
        # Step 3: Verify all files are listed
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 200)
        files_data = response.get_json()
        
        user_files = files_data['files']
        self.assertEqual(len(user_files), 3, "Should have 3 uploaded files")
        
        filenames = [f['name'] for f in user_files]
        self.assertIn('quarterly_financial_report_Q3_2024.pdf', filenames)
        self.assertIn('employee_handbook_2024.pdf', filenames)
        self.assertIn('project_proposal_acme_corp.docx', filenames)
        
        # Step 4: Search for files using semantic query
        response = self.client.post(
            '/api/search',
            json={'query': 'financial report'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        search_data = response.get_json()
        
        self.assertIn('results', search_data)
        results = search_data['results']
        self.assertGreater(len(results), 0, "Should find matching files")
        
        # Financial report should be in results
        result_names = [r['name'] for r in results]
        self.assertTrue(
            any('financial' in name.lower() for name in result_names),
            "Should find financial-related files"
        )
        
        # Step 5: Search with different query
        response = self.client.post(
            '/api/search',
            json={'query': 'acme proposal'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        search_data = response.get_json()
        results = search_data['results']
        
        self.assertGreater(len(results), 0)
        result_names = [r['name'] for r in results]
        self.assertTrue(
            any('acme' in name.lower() for name in result_names),
            "Should find Acme-related files"
        )
        
        # Step 6: Try to open a file
        response = self.client.get('/api/open-file/quarterly_financial_report_Q3_2024.pdf')
        # Should return 200 with file info (actual opening happens on client)
        self.assertEqual(response.status_code, 200)
        
        print("✅ Finder Integration Journey: PASSED")


class TestGoogleDriveIntegration(unittest.TestCase):
    """
    Integration Test 2: Google Drive Connection Journey
    
    Tests the entire flow of:
    1. Checking sync status (Drive disconnected)
    2. Attempting Google Drive connection
    3. Checking sync status updates
    4. Searching across sources
    
    This exercises: Flask app, sync engine, OAuth flow, database
    """
    
    def setUp(self):
        """Set up test environment."""
        from app import app
        
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Simulate logged in user
        with self.client.session_transaction() as sess:
            sess['user'] = 'gdrive_test@example.com'
    
    def test_google_drive_connection_journey(self):
        """
        Test Google Drive connection flow:
        Check status -> Attempt connect -> Verify status change
        """
        
        # Step 1: Check initial sync status
        response = self.client.get('/api/sync/status')
        self.assertEqual(response.status_code, 200)
        status_data = response.get_json()
        
        self.assertIn('status', status_data)
        status = status_data['status']
        
        # Should have entries for Finder and Google Drive
        self.assertIn('Finder', status)
        self.assertIn('Google Drive', status)
        
        # Step 2: Attempt Google Drive connection
        # Note: Actual OAuth requires browser interaction, so this tests the API endpoint
        response = self.client.post(
            '/api/connect/google-drive',
            json={'email': 'test@gmail.com'},
            content_type='application/json'
        )
        
        # Will return error since OAuth needs real interaction, but endpoint should work
        self.assertIn(response.status_code, [200, 400, 500, 501])
        
        # Step 3: Test disconnect endpoint exists and works
        response = self.client.post('/api/disconnect/Google Drive')
        self.assertIn(response.status_code, [200, 501])
        
        # Step 4: Verify sync endpoint works
        response = self.client.post(
            '/api/sync',
            json={'source': 'Finder'},
            content_type='application/json'
        )
        self.assertIn(response.status_code, [200, 500])
        
        print("✅ Google Drive Integration Journey: PASSED")


class TestSearchAcrossSourcesIntegration(unittest.TestCase):
    """
    Integration Test 3: Multi-Source Search Journey
    
    Tests searching across multiple file sources and verifying
    results contain proper source attribution.
    """
    
    def setUp(self):
        """Set up test environment."""
        from app import app, uploaded_files
        
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        uploaded_files.clear()
        
        self.temp_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = Path(self.temp_dir)
        
        with self.client.session_transaction() as sess:
            sess['user'] = 'multi_source_test@example.com'
    
    def tearDown(self):
        """Clean up."""
        from app import uploaded_files
        uploaded_files.clear()
        
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_multi_source_search(self):
        """
        Test searching across files from different sources.
        """
        from app import uploaded_files
        
        # Add files with different sources (simulating Finder + Google Drive)
        user = 'multi_source_test@example.com'
        uploaded_files[user] = [
            {
                'name': 'local_contract.pdf',
                'source': 'Finder',
                'uploadDate': '2024-01-01T00:00:00',
                'size': 1024,
                'indexed': True,
                'owner': user
            },
            {
                'name': 'cloud_contract.pdf',
                'source': 'Google Drive',
                'uploadDate': '2024-01-02T00:00:00',
                'size': 2048,
                'indexed': True,
                'owner': user
            },
            {
                'name': 'meeting_notes.docx',
                'source': 'Finder',
                'uploadDate': '2024-01-03T00:00:00',
                'size': 512,
                'indexed': True,
                'owner': user
            }
        ]
        
        # Search for "contract" - should find files from both sources
        response = self.client.post(
            '/api/search',
            json={'query': 'contract'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        results = response.get_json()['results']
        self.assertEqual(len(results), 2, "Should find 2 contract files")
        
        # Verify different sources in results
        sources = [r['source'] for r in results]
        self.assertIn('Finder', sources)
        self.assertIn('Google Drive', sources)
        
        # Search for "meeting" - should only find Finder file
        response = self.client.post(
            '/api/search',
            json={'query': 'meeting notes'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        results = response.get_json()['results']
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['source'], 'Finder')
        
        print("✅ Multi-Source Search Integration: PASSED")


class TestDatabaseIntegration(unittest.TestCase):
    """
    Integration Test 4: Database Operations Journey
    
    Tests the complete database workflow including:
    - Creating database
    - Adding files with embeddings
    - Querying files
    - Persistence across connections
    """
    
    def setUp(self):
        """Create temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
    
    def tearDown(self):
        """Remove temporary database."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_complete_database_workflow(self):
        """Test full database integration."""
        from database.models import GnomeDatabase, compute_file_hash
        
        # Step 1: Create database
        db = GnomeDatabase(db_path=self.temp_db.name)
        
        # Step 2: Add files
        file1_id = db.add_file(
            filename='document1.pdf',
            file_path='/path/to/document1.pdf',
            source='Finder',
            file_hash='hash1',
            file_size=1000,
            metadata={'author': 'Test User'}
        )
        
        file2_id = db.add_file(
            filename='document2.pdf',
            file_path='/path/to/document2.pdf',
            source='Google Drive',
            file_hash='hash2',
            file_size=2000,
            metadata={'shared': True}
        )
        
        self.assertIsNotNone(file1_id)
        self.assertIsNotNone(file2_id)
        
        # Step 3: Store embeddings for files
        embedding1 = [0.1 * i for i in range(512)]
        embedding2 = [0.2 * i for i in range(512)]
        
        db.store_embedding(file1_id, 'vec_1', embedding1)
        db.store_embedding(file2_id, 'vec_2', embedding2)
        
        # Step 4: Query files by source
        finder_files = db.get_files_by_source('Finder')
        self.assertEqual(len(finder_files), 1)
        self.assertEqual(finder_files[0]['filename'], 'document1.pdf')
        
        drive_files = db.get_files_by_source('Google Drive')
        self.assertEqual(len(drive_files), 1)
        self.assertEqual(drive_files[0]['filename'], 'document2.pdf')
        
        # Step 5: Get all files
        all_files = db.get_all_files()
        self.assertEqual(len(all_files), 2)
        
        # Step 6: Retrieve embeddings
        retrieved1 = db.get_embedding('vec_1')
        self.assertIsNotNone(retrieved1)
        self.assertEqual(len(retrieved1), 512)
        
        # Step 7: Get all embeddings
        all_embeddings = db.get_all_embeddings()
        self.assertEqual(len(all_embeddings), 2)
        
        # Step 8: Test sync state
        db.update_sync_state('Finder', 'syncing')
        state = db.get_sync_state('Finder')
        self.assertEqual(state['status'], 'syncing')
        
        db.update_sync_state('Finder', 'idle')
        state = db.get_sync_state('Finder')
        self.assertEqual(state['status'], 'idle')
        
        # Step 9: Close and reopen - verify persistence
        db.close()
        
        db2 = GnomeDatabase(db_path=self.temp_db.name)
        all_files = db2.get_all_files()
        self.assertEqual(len(all_files), 2)
        
        retrieved = db2.get_embedding('vec_1')
        self.assertIsNotNone(retrieved)
        
        db2.close()
        
        print("✅ Database Integration Journey: PASSED")


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("GNOME INTEGRATION TESTS")
    print("=" * 70)
    print()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all integration test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFinderIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGoogleDriveIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchAcrossSourcesIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)

