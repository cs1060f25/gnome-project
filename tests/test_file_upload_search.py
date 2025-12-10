"""
Unit tests for File Upload & Search feature (CS1060-200)

Tests cover:
- File upload functionality
- Search API endpoints
- File listing
- Authentication requirements
- File type validation
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from io import BytesIO
import sys

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, uploaded_files, users
from werkzeug.security import generate_password_hash


class TestFileUploadSearch(unittest.TestCase):
    """Test suite for File Upload & Search functionality."""
    
    def setUp(self):
        """Set up test client and test data."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # Clear uploaded files before each test
        uploaded_files.clear()
        
        # Create test upload folder
        self.test_upload_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = Path(self.test_upload_dir)
        
    def tearDown(self):
        """Clean up after tests."""
        # Clear uploaded files
        uploaded_files.clear()
        
        # Remove test upload directory
        import shutil
        if os.path.exists(self.test_upload_dir):
            shutil.rmtree(self.test_upload_dir)
    
    def login(self):
        """Helper method to log in for authenticated tests."""
        with self.client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
    
    def test_login_required_for_index(self):
        """Test that index page requires authentication."""
        response = self.client.get('/')
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=False)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    def test_login_failure(self):
        """Test failed login with wrong credentials."""
        response = self.client.post('/login', data={
            'email': 'wrong@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 401)
    
    def test_file_upload_without_auth(self):
        """Test that file upload requires authentication."""
        data = {
            'file': (BytesIO(b'test content'), 'test.pdf')
        }
        response = self.client.post('/api/upload', data=data)
        self.assertEqual(response.status_code, 401)
    
    def test_file_upload_success(self):
        """Test successful file upload."""
        self.login()
        
        # Create a test file
        data = {
            'file': (BytesIO(b'This is a test PDF content'), 'test_document.pdf')
        }
        
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertIn('Successfully uploaded', json_data['message'])
        
        # Verify file was added to user's uploaded_files
        user_files = uploaded_files.get('test@example.com', [])
        self.assertEqual(len(user_files), 1)
        self.assertEqual(user_files[0]['name'], 'test_document.pdf')
        self.assertEqual(user_files[0]['source'], 'Finder')
        self.assertEqual(user_files[0]['owner'], 'test@example.com')
    
    def test_file_upload_no_file(self):
        """Test file upload with no file provided."""
        self.login()
        
        response = self.client.post('/api/upload',
                                    data={},
                                    content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertIn('No file selected', json_data['error'])
    
    def test_file_upload_invalid_extension(self):
        """Test file upload with invalid file extension."""
        self.login()
        
        data = {
            'file': (BytesIO(b'malicious content'), 'malware.exe')
        }
        
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertIn('File type not allowed', json_data['error'])
    
    def test_api_files_without_auth(self):
        """Test that /api/files requires authentication."""
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 401)
    
    def test_api_files_list(self):
        """Test retrieving list of files."""
        self.login()
        
        # Add some test files for current user
        user_email = 'test@example.com'
        uploaded_files[user_email] = [
            {
                'name': 'file1.pdf',
                'source': 'Finder',
                'uploadDate': '2024-01-01T00:00:00',
                'size': 1024,
                'indexed': True,
                'owner': user_email
            },
            {
                'name': 'file2.docx',
                'source': 'Finder',
                'uploadDate': '2024-01-02T00:00:00',
                'size': 2048,
                'indexed': True,
                'owner': user_email
            }
        ]
        
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 200)
        
        json_data = json.loads(response.data)
        self.assertIn('files', json_data)
        self.assertEqual(len(json_data['files']), 2)
        self.assertIn('syncStatus', json_data)
    
    def test_search_without_auth(self):
        """Test that search requires authentication."""
        response = self.client.post('/api/search',
                                    json={'query': 'test'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 401)
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        self.login()
        
        response = self.client.post('/api/search',
                                    json={'query': ''},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_search_exact_match(self):
        """Test search with exact filename match."""
        self.login()
        
        # Add test files for current user
        user_email = 'test@example.com'
        uploaded_files[user_email] = [
            {
                'name': 'project_report.pdf',
                'source': 'Finder',
                'uploadDate': '2024-01-01T00:00:00',
                'size': 1024,
                'indexed': True,
                'owner': user_email
            },
            {
                'name': 'meeting_notes.docx',
                'source': 'Finder',
                'uploadDate': '2024-01-02T00:00:00',
                'size': 2048,
                'indexed': True,
                'owner': user_email
            }
        ]
        
        response = self.client.post('/api/search',
                                    json={'query': 'project_report.pdf'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertIn('results', json_data)
        
        # Should find exact match
        results = json_data['results']
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['name'], 'project_report.pdf')
        self.assertEqual(results[0]['similarity'], 1.0)
    
    def test_search_partial_match(self):
        """Test search with partial keyword match."""
        self.login()
        
        # Add test files for current user
        user_email = 'test@example.com'
        uploaded_files[user_email] = [
            {
                'name': 'annual_report_2024.pdf',
                'source': 'Finder',
                'uploadDate': '2024-01-01T00:00:00',
                'size': 1024,
                'indexed': True,
                'owner': user_email
            },
            {
                'name': 'meeting_notes.docx',
                'source': 'Finder',
                'uploadDate': '2024-01-02T00:00:00',
                'size': 2048,
                'indexed': True,
                'owner': user_email
            }
        ]
        
        response = self.client.post('/api/search',
                                    json={'query': 'report'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        results = json_data['results']
        
        # Should find files containing 'report'
        self.assertGreater(len(results), 0)
        self.assertIn('report', results[0]['name'].lower())
        self.assertGreater(results[0]['similarity'], 0)
    
    def test_search_no_results(self):
        """Test search with no matching results."""
        self.login()
        
        # Add test files for current user
        user_email = 'test@example.com'
        uploaded_files[user_email] = [
            {
                'name': 'document.pdf',
                'source': 'Finder',
                'uploadDate': '2024-01-01T00:00:00',
                'size': 1024,
                'indexed': True,
                'owner': user_email
            }
        ]
        
        response = self.client.post('/api/search',
                                    json={'query': 'nonexistent'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['results']), 0)
    
    def test_open_file_without_auth(self):
        """Test that opening files requires authentication."""
        response = self.client.get('/api/open-file/test.pdf')
        self.assertEqual(response.status_code, 401)
    
    def test_open_file_not_found(self):
        """Test opening a file that doesn't exist."""
        self.login()
        
        response = self.client.get('/api/open-file/nonexistent.pdf')
        self.assertEqual(response.status_code, 404)
    
    def test_open_file_success(self):
        """Test successfully opening a file."""
        self.login()
        
        # Add a test file for current user
        user_email = 'test@example.com'
        test_file_path = os.path.join(self.test_upload_dir, 'test.pdf')
        uploaded_files[user_email] = [
            {
                'name': 'test.pdf',
                'source': 'Finder',
                'file_path': test_file_path,
                'indexed': True,
                'owner': user_email
            }
        ]
        
        response = self.client.get('/api/open-file/test.pdf')
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertIn('file_path', json_data)
    
    def test_logout(self):
        """Test logout functionality."""
        self.login()
        
        response = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        
        # Verify session is cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('user', sess)
    
    def test_duplicate_filename_handling(self):
        """
        Test that uploading a file with the same name updates the existing entry
        instead of creating a duplicate. This tests the fix for the duplicate
        filename handling bug.
        """
        self.login()
        
        # Upload a file
        data = {
            'file': (BytesIO(b'Version 1 content'), 'document.pdf')
        }
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        
        # Verify file was added
        user_files = uploaded_files.get('test@example.com', [])
        self.assertEqual(len(user_files), 1)
        first_upload_date = user_files[0]['uploadDate']
        
        # Upload same filename again with different content
        data = {
            'file': (BytesIO(b'Version 2 content - updated'), 'document.pdf')
        }
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertIn('re-uploaded', json_data['message'].lower())
        
        # Verify only ONE entry exists (no duplicate)
        user_files = uploaded_files.get('test@example.com', [])
        self.assertEqual(len(user_files), 1)
        
        # Verify the entry was updated (different upload date)
        second_upload_date = user_files[0]['uploadDate']
        self.assertNotEqual(first_upload_date, second_upload_date)
        
        # Verify file list API returns only one file
        response = self.client.get('/api/files')
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['files']), 1)
        self.assertEqual(json_data['files'][0]['name'], 'document.pdf')
        
        # Verify search returns only one result
        response = self.client.post('/api/search',
                                    json={'query': 'document'},
                                    content_type='application/json')
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['results']), 1)
    
    def test_user_file_isolation(self):
        """
        Test that users can only see and access their own files.
        This tests the fix for the user file isolation bug.
        """
        # Create second user
        users['other@example.com'] = generate_password_hash('password456')
        
        # Login as first user and upload a file
        with self.client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        data = {
            'file': (BytesIO(b'User 1 private file'), 'user1_private.pdf')
        }
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        
        # Verify first user can see their file
        response = self.client.get('/api/files')
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['files']), 1)
        self.assertEqual(json_data['files'][0]['name'], 'user1_private.pdf')
        
        # Logout and login as second user
        self.client.get('/logout')
        with self.client.session_transaction() as sess:
            sess['user'] = 'other@example.com'
        
        # Upload a file as second user
        data = {
            'file': (BytesIO(b'User 2 private file'), 'user2_private.pdf')
        }
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        
        # Verify second user can ONLY see their own file, not user1's file
        response = self.client.get('/api/files')
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['files']), 1)
        self.assertEqual(json_data['files'][0]['name'], 'user2_private.pdf')
        self.assertNotIn('user1_private.pdf', [f['name'] for f in json_data['files']])
        
        # Try to search - should only find user2's files
        response = self.client.post('/api/search',
                                    json={'query': 'private'},
                                    content_type='application/json')
        json_data = json.loads(response.data)
        self.assertEqual(len(json_data['results']), 1)
        self.assertEqual(json_data['results'][0]['name'], 'user2_private.pdf')
        
        # Try to open user1's file as user2 - should fail
        response = self.client.get('/api/open-file/user1_private.pdf')
        self.assertEqual(response.status_code, 404)  # File not found (for this user)


if __name__ == '__main__':
    unittest.main()

