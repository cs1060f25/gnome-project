"""
Test suite for dashboard rendering - BUG CS1060-154
Tests that the dashboard renders correctly after successful login.

This test was generated to reproduce and validate the fix for:
BUG CS1060-154: Dashboard not rendering after successful login

Expected behavior: Dashboard should load with search bar, file views, and no errors
Actual behavior (before fix): Dashboard shows blank screen or fails to initialize Vue
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


class TestDashboardRendering(unittest.TestCase):
    """Test dashboard rendering after login"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Login to get session
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
    
    def test_index_route_redirects_when_not_logged_in(self):
        """Test that index redirects to login when not authenticated"""
        # Create new client without login
        client = self.app.test_client()
        response = client.get('/', follow_redirects=False)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    
    def test_index_route_renders_when_logged_in(self):
        """Test that index renders dashboard when authenticated"""
        response = self.client.get('/')
        
        # Should successfully render
        self.assertEqual(response.status_code, 200)
        
        # Should contain dashboard HTML
        html = response.data.decode('utf-8')
        self.assertIn('<div id="app">', html)
        self.assertIn('Search', html)  # Search placeholder
        self.assertIn('vue.global.js', html)  # Vue.js loaded
    
    def test_dashboard_has_vue_app_initialization(self):
        """Test that dashboard includes Vue.js app initialization"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for Vue.js initialization
        self.assertIn('createApp', html)
        self.assertIn('.mount(\'#app\')', html)
        
        # Check for required data properties
        self.assertIn('currentView', html)
        self.assertIn('files', html)
        self.assertIn('searchResults', html)
    
    def test_dashboard_has_mounted_hook(self):
        """Test that Vue app has mounted hook to fetch files"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for mounted hook
        self.assertIn('mounted()', html)
        self.assertIn('this.fetchFiles()', html)
    
    def test_dashboard_has_search_bar(self):
        """Test that dashboard includes search bar element"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for search input
        self.assertIn('search-input', html)
        self.assertIn('performSearch', html)
        self.assertIn('v-model="searchQuery"', html)
    
    def test_dashboard_has_file_view_sections(self):
        """Test that dashboard has file viewing sections"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for file views
        self.assertIn('ecosystem-cards-container', html)  # File browser
        self.assertIn('search-results-view', html)  # Search results
        self.assertIn('settings-view', html)  # Settings
    
    def test_dashboard_has_navigation(self):
        """Test that dashboard includes sidebar navigation"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for navigation
        self.assertIn('sidebar', html)
        self.assertIn('Files', html)
        self.assertIn('Settings', html)
    
    def test_dashboard_loads_with_api_endpoints(self):
        """Test that dashboard can call API endpoints"""
        # Test /api/files endpoint (used on dashboard load)
        response = self.client.get('/api/files')
        
        # Should return JSON
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        # Should have files and syncStatus
        data = response.get_json()
        self.assertIn('files', data)
        self.assertIn('syncStatus', data)
    
    def test_search_api_endpoint_works(self):
        """Test that search API endpoint functions correctly"""
        response = self.client.post('/api/search', 
                                   json={'query': 'test', 'top_k': 10})
        
        # Should return JSON with results
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)
    
    def test_dashboard_has_loading_indicator(self):
        """Test that dashboard includes loading/progress indicator"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for progress bar
        self.assertIn('progress-bar-container', html)
        self.assertIn('v-if="loading"', html)
    
    def test_dashboard_has_toast_notifications(self):
        """Test that dashboard includes toast notification system"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for toast
        self.assertIn('toast', html)
        self.assertIn('showToast', html)
    
    def test_dashboard_css_loads_correctly(self):
        """Test that dashboard CSS is included"""
        response = self.client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for key CSS classes
        self.assertIn('.app-container', html)
        self.assertIn('.sidebar', html)
        self.assertIn('.main-content', html)
        self.assertIn('.search-input', html)


class TestDashboardAPIIntegration(unittest.TestCase):
    """Test dashboard API integration"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Login
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
    
    def test_files_api_returns_correct_structure(self):
        """Test that /api/files returns correct data structure"""
        response = self.client.get('/api/files')
        data = response.get_json()
        
        # Check structure
        self.assertIsInstance(data['files'], list)
        self.assertIsInstance(data['syncStatus'], dict)
        
        # If files exist, check their structure
        if data['files']:
            file = data['files'][0]
            self.assertIn('name', file)
            self.assertIn('uploadDate', file)
    
    def test_search_returns_results_with_similarity(self):
        """Test that search returns results with similarity scores"""
        # First upload a file
        import io
        file_data = io.BytesIO(b"test content")
        file_data.name = 'test.txt'
        
        self.client.post('/api/upload', 
                        data={'file': (file_data, 'test.txt')})
        
        # Now search
        response = self.client.post('/api/search',
                                   json={'query': 'test'})
        data = response.get_json()
        
        # Should have results
        self.assertIn('results', data)
        
        # If results, they should have similarity score
        if data['results']:
            result = data['results'][0]
            self.assertIn('similarity', result)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 70)
    print("BUG CS1060-154: Test Dashboard Rendering After Login")
    print("=" * 70)
    print()
    run_tests()

