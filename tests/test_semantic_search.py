"""
Test suite for semantic search functionality
HW8 Feature: AI Embeddings and Semantic Search
"""
import unittest
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantic.advanced_search import BM25Scorer, QueryExpander, AdvancedReranker, advanced_search
from semantic.hybrid_search import calculate_keyword_score, hybrid_search_rerank, filter_by_relevance
from semantic.vector_database import VectorDatabase, create_vector_database


class TestBM25Scorer(unittest.TestCase):
    """Test BM25 scoring algorithm"""
    
    def setUp(self):
        self.scorer = BM25Scorer()
        self.documents = [
            {'name': 'resume_2024.pdf', 'content': 'software engineer with python experience'},
            {'name': 'tax_return.pdf', 'content': '1040 tax form for 2023'},
            {'name': 'presentation.pptx', 'content': 'quarterly business review slides'},
        ]
        self.scorer.fit(self.documents)
    
    def test_tokenize(self):
        """Test text tokenization"""
        tokens = self.scorer.tokenize("Hello, World! This is a test.")
        self.assertIn('hello', tokens)
        self.assertIn('world', tokens)
        self.assertIn('test', tokens)
    
    def test_score_calculation(self):
        """Test BM25 score calculation"""
        score = self.scorer.score("resume software engineer", self.documents[0])
        self.assertGreater(score, 0)
        
        # Resume should score higher for "resume" query than tax return
        resume_score = self.scorer.score("resume", self.documents[0])
        tax_score = self.scorer.score("resume", self.documents[1])
        self.assertGreater(resume_score, tax_score)


class TestQueryExpander(unittest.TestCase):
    """Test query expansion with synonyms"""
    
    def setUp(self):
        self.expander = QueryExpander()
    
    def test_synonym_expansion(self):
        """Test that synonyms are added to queries"""
        expanded = self.expander.expand("resume")
        self.assertIn("resume", expanded)
        # Should include synonyms like cv, bio
        self.assertTrue(len(expanded) > 1)
    
    def test_no_expansion_for_unknown_words(self):
        """Test that unknown words don't get expanded"""
        expanded = self.expander.expand("xyzabc123")
        self.assertEqual(["xyzabc123"], expanded)
    
    def test_expand_query_string(self):
        """Test query string expansion"""
        expanded_str = self.expander.expand_query_string("photo resume")
        self.assertIsInstance(expanded_str, str)
        self.assertTrue(len(expanded_str) > len("photo resume"))


class TestAdvancedReranker(unittest.TestCase):
    """Test advanced reranking functionality"""
    
    def setUp(self):
        self.reranker = AdvancedReranker()
        self.results = [
            {'name': 'resume.pdf', 'similarity': 0.7, 'uploadDate': '2024-01-15T10:00:00'},
            {'name': 'other_doc.pdf', 'similarity': 0.8, 'uploadDate': '2023-01-15T10:00:00'},
            {'name': 'resume_2024.pdf', 'similarity': 0.6, 'uploadDate': '2024-11-01T10:00:00'},
        ]
    
    def test_rerank(self):
        """Test that reranking produces final scores"""
        reranked = self.reranker.rerank("resume", self.results)
        
        # All results should have final scores
        for result in reranked:
            self.assertIn('final_score', result)
            self.assertIn('score_breakdown', result)
        
        # Results should be sorted by final_score
        scores = [r['final_score'] for r in reranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_exact_match_boost(self):
        """Test that exact matches get boosted"""
        exact_score = self.reranker._calculate_exact_match("resume", {'name': 'resume.pdf'})
        partial_score = self.reranker._calculate_exact_match("resume", {'name': 'my_resume_doc.pdf'})
        no_match_score = self.reranker._calculate_exact_match("resume", {'name': 'taxes.pdf'})
        
        self.assertGreater(exact_score, partial_score)
        self.assertGreater(partial_score, no_match_score)


class TestHybridSearch(unittest.TestCase):
    """Test hybrid search functionality"""
    
    def test_calculate_keyword_score(self):
        """Test keyword score calculation"""
        # Exact match
        score = calculate_keyword_score("resume", "resume.pdf")
        self.assertGreater(score, 0.9)
        
        # Partial match
        score = calculate_keyword_score("resume", "my_resume_2024.pdf")
        self.assertGreater(score, 0.5)
        
        # No match
        score = calculate_keyword_score("resume", "taxes.pdf")
        self.assertLess(score, 0.3)
    
    def test_hybrid_search_rerank(self):
        """Test hybrid search reranking"""
        results = [
            {'name': 'resume.pdf', 'similarity': 0.5},
            {'name': 'taxes.pdf', 'similarity': 0.8},
        ]
        
        reranked = hybrid_search_rerank("resume", results)
        
        # Resume should be ranked higher even though it had lower semantic score
        self.assertEqual(reranked[0]['name'], 'resume.pdf')
    
    def test_filter_by_relevance(self):
        """Test relevance filtering"""
        results = [
            {'name': 'file1.pdf', 'similarity': 0.9},
            {'name': 'file2.pdf', 'similarity': 0.1},
            {'name': 'file3.pdf', 'similarity': 0.05},
        ]
        
        filtered = filter_by_relevance(results, min_score=0.15)
        self.assertEqual(len(filtered), 2)


class TestVectorDatabase(unittest.TestCase):
    """Test vector database functionality"""
    
    def setUp(self):
        self.db = VectorDatabase()
    
    def test_store_and_search(self):
        """Test storing and searching embeddings"""
        # Store some vectors
        self.db.store_embedding('file1', [1.0, 0.0, 0.0], {'name': 'resume.pdf'})
        self.db.store_embedding('file2', [0.0, 1.0, 0.0], {'name': 'taxes.pdf'})
        self.db.store_embedding('file3', [0.9, 0.1, 0.0], {'name': 'cv.pdf'})
        
        # Search with query similar to file1
        results = self.db.search([1.0, 0.0, 0.0], top_k=2)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 'file1')  # Most similar
        self.assertGreater(results[0]['similarity'], results[1]['similarity'])
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        # Identical vectors
        sim = self.db._cosine_similarity([1, 0, 0], [1, 0, 0])
        self.assertAlmostEqual(sim, 1.0)
        
        # Orthogonal vectors
        sim = self.db._cosine_similarity([1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(sim, 0.0)
        
        # Similar vectors
        sim = self.db._cosine_similarity([1, 0, 0], [0.9, 0.1, 0])
        self.assertGreater(sim, 0.8)
    
    def test_delete_embedding(self):
        """Test deleting embeddings"""
        self.db.store_embedding('file1', [1.0, 0.0, 0.0], {})
        self.assertEqual(len(self.db.list_files()), 1)
        
        self.db.delete_embedding('file1')
        self.assertEqual(len(self.db.list_files()), 0)
    
    def test_get_stats(self):
        """Test database statistics"""
        self.db.store_embedding('file1', [1.0, 0.0, 0.0, 0.0], {})
        stats = self.db.get_stats()
        
        self.assertEqual(stats['total_vectors'], 1)
        self.assertEqual(stats['vector_dimension'], 4)


class TestAdvancedSearch(unittest.TestCase):
    """Test end-to-end advanced search"""
    
    def test_advanced_search_integration(self):
        """Test full advanced search pipeline"""
        results = [
            {'name': 'resume_2024.pdf', 'similarity': 0.7, 'uploadDate': '2024-11-01T10:00:00'},
            {'name': 'old_resume.pdf', 'similarity': 0.8, 'uploadDate': '2020-01-01T10:00:00'},
            {'name': 'taxes.pdf', 'similarity': 0.6, 'uploadDate': '2024-10-01T10:00:00'},
        ]
        
        corpus = results  # Full corpus for BM25
        
        reranked = advanced_search("resume", results, full_corpus=corpus)
        
        # Should have results
        self.assertGreater(len(reranked), 0)
        
        # All results should have final scores
        for result in reranked:
            self.assertIn('final_score', result)
        
        # Recent resume with exact match should rank high
        top_result = reranked[0]
        self.assertIn('resume', top_result['name'].lower())


class TestFileProcessorHelper(unittest.TestCase):
    """Test file processor helper functions"""
    
    def test_supported_extensions(self):
        """Test supported file extension list"""
        from semantic.file_processor import get_supported_extensions, is_supported_file
        
        extensions = get_supported_extensions()
        self.assertIn('.pdf', extensions)
        self.assertIn('.docx', extensions)
        self.assertIn('.txt', extensions)
    
    def test_is_supported_file(self):
        """Test file support checking"""
        from semantic.file_processor import is_supported_file
        
        self.assertTrue(is_supported_file('document.pdf'))
        self.assertTrue(is_supported_file('image.jpg'))
        self.assertFalse(is_supported_file('.hidden'))
        self.assertFalse(is_supported_file('file.xyz'))


def run_tests():
    """Run all tests"""
    unittest.main()


if __name__ == '__main__':
    run_tests()

