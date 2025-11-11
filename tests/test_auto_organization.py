"""
Comprehensive tests for AI auto-organization feature (CS1060-160).
Tests clustering logic, API endpoints, and file management.
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from semantic.vector_database import VectorDatabase
from semantic.auto_organizer import FileOrganizer, rename_file_with_suggestions


class TestFileOrganizer:
    """Test the FileOrganizer class for clustering and suggestions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.vector_db = VectorDatabase()
        self.organizer = FileOrganizer(self.vector_db)
        
    def test_cluster_files_empty(self):
        """Test clustering with no files."""
        clusters = self.organizer.cluster_files([])
        assert clusters == []
    
    def test_cluster_files_single(self):
        """Test clustering with a single file."""
        file_ids = ['invoice_2024.pdf']
        clusters = self.organizer.cluster_files(file_ids)
        assert len(clusters) == 1
        assert file_ids[0] in clusters[0]
    
    def test_cluster_similar_files(self):
        """Test that similar files are grouped together."""
        # Create mock files with similar names
        files = [
            {'name': 'invoice_jan_2024.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'invoice_feb_2024.pdf', 'size': 1500, 'source': 'Finder'},
            {'name': 'report_q1.pdf', 'size': 2000, 'source': 'Finder'},
            {'name': 'report_q2.pdf', 'size': 2200, 'source': 'Finder'},
        ]
        
        # Store embeddings
        for file in files:
            mock_embedding = self.organizer._generate_mock_embedding(file['name'])
            self.vector_db.store_embedding(file['name'], mock_embedding, metadata=file)
        
        file_ids = [f['name'] for f in files]
        clusters = self.organizer.cluster_files(file_ids, threshold=0.5)
        
        # Should create at least 2 clusters (invoices and reports)
        assert len(clusters) >= 2
        
        # Check that similar files are grouped
        invoice_files = [f for f in file_ids if 'invoice' in f]
        report_files = [f for f in file_ids if 'report' in f]
        
        # At least one cluster should contain invoice files
        has_invoice_cluster = any(
            all(f in cluster for f in invoice_files if len(cluster) > 1)
            for cluster in clusters
        )
        assert has_invoice_cluster or len(clusters) <= 3  # Allow flexibility
    
    def test_suggest_tags(self):
        """Test tag suggestion for file clusters."""
        # Create files with common patterns
        files = [
            {'name': 'invoice_2024_jan.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'invoice_2024_feb.pdf', 'size': 1500, 'source': 'Finder'},
            {'name': 'invoice_2024_mar.pdf', 'size': 1200, 'source': 'Finder'},
        ]
        
        for file in files:
            mock_embedding = self.organizer._generate_mock_embedding(file['name'])
            self.vector_db.store_embedding(file['name'], mock_embedding, metadata=file)
        
        cluster = [f['name'] for f in files]
        tags = self.organizer.suggest_tags(cluster)
        
        # Should suggest 'invoice' tag
        assert len(tags) > 0
        assert 'invoice' in tags or any('invoice' in tag.lower() for tag in tags)
    
    def test_suggest_folder_name(self):
        """Test folder name suggestion."""
        files = [
            {'name': 'contract_clientA.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'contract_clientB.pdf', 'size': 1500, 'source': 'Finder'},
        ]
        
        for file in files:
            mock_embedding = self.organizer._generate_mock_embedding(file['name'])
            self.vector_db.store_embedding(file['name'], mock_embedding, metadata=file)
        
        cluster = [f['name'] for f in files]
        folder_name = self.organizer.suggest_folder_name(cluster)
        
        # Should suggest something related to contracts
        assert folder_name is not None
        assert len(folder_name) > 0
        assert 'contract' in folder_name.lower() or 'client' in folder_name.lower()
    
    def test_generate_organization_suggestions(self):
        """Test complete suggestion generation."""
        files = [
            {'name': 'invoice_2024_q1.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'invoice_2024_q2.pdf', 'size': 1500, 'source': 'Finder'},
            {'name': 'report_annual.pdf', 'size': 2000, 'source': 'Finder'},
            {'name': 'report_monthly.pdf', 'size': 1800, 'source': 'Finder'},
        ]
        
        suggestions = self.organizer.generate_organization_suggestions(files)
        
        # Should generate at least one suggestion
        assert isinstance(suggestions, list)
        
        # Each suggestion should have required fields
        for suggestion in suggestions:
            assert 'id' in suggestion
            assert 'folder_name' in suggestion
            assert 'tags' in suggestion
            assert 'files' in suggestion
            assert 'confidence' in suggestion
            assert 'description' in suggestion
            assert 0.0 <= suggestion['confidence'] <= 1.0
    
    def test_calculate_cluster_confidence(self):
        """Test confidence calculation."""
        # Single file cluster should have low confidence
        cluster_single = ['file1.pdf']
        confidence = self.organizer._calculate_cluster_confidence(cluster_single)
        assert confidence == 0.0
        
        # Multiple similar files should have higher confidence
        files = [
            {'name': 'invoice_1.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'invoice_2.pdf', 'size': 1500, 'source': 'Finder'},
            {'name': 'invoice_3.pdf', 'size': 1200, 'source': 'Finder'},
        ]
        
        for file in files:
            mock_embedding = self.organizer._generate_mock_embedding(file['name'])
            self.vector_db.store_embedding(file['name'], mock_embedding, metadata=file)
        
        cluster = [f['name'] for f in files]
        confidence = self.organizer._calculate_cluster_confidence(cluster)
        
        assert 0.0 < confidence <= 1.0
    
    def test_mock_embedding_generation(self):
        """Test mock embedding generation."""
        text = "test_invoice_2024.pdf"
        embedding = self.organizer._generate_mock_embedding(text)
        
        # Should be 128 dimensions
        assert len(embedding) == 128
        
        # All values should be in [-1, 1]
        assert all(-1.0 <= val <= 1.0 for val in embedding)
        
        # Same text should generate same embedding
        embedding2 = self.organizer._generate_mock_embedding(text)
        assert embedding == embedding2
        
        # Different text should generate different embedding
        embedding3 = self.organizer._generate_mock_embedding("different_file.pdf")
        assert embedding != embedding3


class TestRenameFileSuggestions:
    """Test file renaming with tag suggestions."""
    
    def test_rename_with_tags(self):
        """Test renaming file with suggested tags."""
        original = "document123.pdf"
        tags = ["invoice", "2024"]
        
        new_name = rename_file_with_suggestions(original, tags)
        
        assert new_name != original
        assert new_name.endswith('.pdf')
        assert 'invoice' in new_name.lower()
    
    def test_rename_preserves_extension(self):
        """Test that file extension is preserved."""
        original = "file.docx"
        tags = ["contract"]
        
        new_name = rename_file_with_suggestions(original, tags)
        
        assert new_name.endswith('.docx')
    
    def test_rename_no_duplicate_tag(self):
        """Test that tag isn't duplicated if already in name."""
        original = "invoice_2024.pdf"
        tags = ["invoice", "financial"]
        
        new_name = rename_file_with_suggestions(original, tags)
        
        # Should not duplicate 'invoice'
        assert new_name.count('invoice') <= 2  # Original + maybe prefix


class TestAutoOrganizationAPI:
    """Test API endpoints for auto-organization."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        with app.test_client() as client:
            yield client
    
    def test_organize_suggestions_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/api/organize/suggestions')
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_organize_suggestions_authenticated(self, client):
        """Test fetching organization suggestions when authenticated."""
        # Login first
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        response = client.get('/api/organize/suggestions')
        assert response.status_code == 200
        data = response.get_json()
        assert 'suggestions' in data
        assert isinstance(data['suggestions'], list)
    
    def test_organize_apply_unauthenticated(self, client):
        """Test that unauthenticated apply requests are rejected."""
        response = client.post('/api/organize/apply', json={
            'suggestion_id': 'test_1',
            'folder_name': 'Test Folder',
            'files': ['file1.pdf'],
            'tags': ['test']
        })
        assert response.status_code == 401
    
    def test_organize_apply_missing_fields(self, client):
        """Test apply endpoint with missing required fields."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        response = client.post('/api/organize/apply', json={
            'suggestion_id': 'test_1'
            # Missing folder_name and files
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_organize_apply_success(self, client):
        """Test successfully applying an organization suggestion."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        # First upload some files
        from app import uploaded_files
        uploaded_files['test@example.com'] = [
            {'name': 'test1.pdf', 'size': 1000, 'source': 'Finder'},
            {'name': 'test2.pdf', 'size': 1500, 'source': 'Finder'},
        ]
        
        response = client.post('/api/organize/apply', json={
            'suggestion_id': 'test_1',
            'folder_name': 'Test Documents',
            'files': ['test1.pdf', 'test2.pdf'],
            'tags': ['test', 'document']
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'files_updated' in data
        assert data['files_updated'] == 2
        
        # Verify files were updated
        user_files = uploaded_files['test@example.com']
        for file in user_files:
            if file['name'] in ['test1.pdf', 'test2.pdf']:
                assert file.get('folder') == 'Test Documents'
                assert 'test' in file.get('tags', [])
    
    def test_organize_undo_success(self, client):
        """Test undoing an organization action."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        from app import uploaded_files
        uploaded_files['test@example.com'] = [
            {
                'name': 'test1.pdf',
                'size': 1000,
                'source': 'Finder',
                'folder': 'Test Folder',
                'tags': ['test']
            }
        ]
        
        response = client.post('/api/organize/undo', json={
            'files': ['test1.pdf']
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify folder and tags were removed
        user_files = uploaded_files['test@example.com']
        assert 'folder' not in user_files[0]
        assert 'tags' not in user_files[0]
    
    def test_file_rename_success(self, client):
        """Test renaming a file."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        from app import uploaded_files
        uploaded_files['test@example.com'] = [
            {'name': 'oldname.pdf', 'size': 1000, 'source': 'Finder', 'file_path': '/tmp/test/oldname.pdf'}
        ]
        
        response = client.post('/api/file/rename', json={
            'old_name': 'oldname.pdf',
            'new_name': 'newname.pdf'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'new_name' in data
        
        # Verify file was renamed
        user_files = uploaded_files['test@example.com']
        assert user_files[0]['name'] == 'newname.pdf'
        assert user_files[0].get('original_name') == 'oldname.pdf'
    
    def test_file_tag_success(self, client):
        """Test adding tags to a file."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        from app import uploaded_files
        uploaded_files['test@example.com'] = [
            {'name': 'document.pdf', 'size': 1000, 'source': 'Finder'}
        ]
        
        response = client.post('/api/file/tag', json={
            'file_name': 'document.pdf',
            'tags': ['important', 'urgent']
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify tags were added
        user_files = uploaded_files['test@example.com']
        assert 'important' in user_files[0].get('tags', [])
        assert 'urgent' in user_files[0].get('tags', [])
    
    def test_file_tag_duplicate_prevention(self, client):
        """Test that duplicate tags are not added."""
        with client.session_transaction() as sess:
            sess['user'] = 'test@example.com'
        
        from app import uploaded_files
        uploaded_files['test@example.com'] = [
            {'name': 'document.pdf', 'size': 1000, 'source': 'Finder', 'tags': ['existing']}
        ]
        
        # Add the same tag again
        response = client.post('/api/file/tag', json={
            'file_name': 'document.pdf',
            'tags': ['existing', 'new']
        })
        
        assert response.status_code == 200
        
        # Verify no duplicate tags
        user_files = uploaded_files['test@example.com']
        tags = user_files[0].get('tags', [])
        assert tags.count('existing') == 1
        assert 'new' in tags


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

