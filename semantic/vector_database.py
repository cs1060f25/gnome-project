"""
Vector database interface for storing and searching embeddings.
This is a generic interface that can work with any vector database.
Pinecone-specific code has been removed.
"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Generic vector database interface.
    Implement specific database connections as needed.
    """
    
    def __init__(self, database_client=None):
        """
        Initialize vector database.
        
        Args:
            database_client: Optional database client (e.g., Pinecone, Weaviate, etc.)
        """
        self.client = database_client
        self.vectors = {}  # In-memory fallback storage
    
    def store_embedding(self, file_id: str, embedding: List[float], metadata: Dict = None) -> None:
        """
        Store an embedding vector with metadata.
        
        Args:
            file_id: Unique identifier for the file
            embedding: Embedding vector
            metadata: Optional metadata (filename, upload_date, etc.)
        """
        if not file_id:
            raise ValueError("No file ID was provided.")
        if not embedding:
            raise ValueError("No embedding was provided.")
        
        # Store in memory (replace with actual database operations)
        self.vectors[file_id] = {
            'embedding': embedding,
            'metadata': metadata or {}
        }
        
        logger.info(f"Stored embedding for file: {file_id}")
    
    def search(self, query_embedding: List[float], top_k: int = 10, namespace: str = None) -> List[Dict]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            namespace: Optional namespace for multi-user support
        
        Returns:
            List of matches with similarity scores
        """
        if not query_embedding:
            raise ValueError("No query embedding was provided.")
        
        # Simple cosine similarity search in memory
        # Replace with actual vector database query
        results = []
        
        for file_id, data in self.vectors.items():
            similarity = self._cosine_similarity(query_embedding, data['embedding'])
            results.append({
                'id': file_id,
                'similarity': similarity,
                'metadata': data['metadata'],
                **data['metadata']  # Unpack metadata for easier access
            })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]
    
    def delete_embedding(self, file_id: str) -> None:
        """
        Delete an embedding from the database.
        
        Args:
            file_id: ID of the file to delete
        """
        if file_id in self.vectors:
            del self.vectors[file_id]
            logger.info(f"Deleted embedding for file: {file_id}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Similarity score between 0 and 1
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same dimension")
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        # Cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def list_files(self, namespace: str = None) -> List[str]:
        """
        List all stored file IDs.
        
        Args:
            namespace: Optional namespace filter
        
        Returns:
            List of file IDs
        """
        return list(self.vectors.keys())
    
    def get_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            'total_vectors': len(self.vectors),
            'vector_dimension': len(list(self.vectors.values())[0]['embedding']) if self.vectors else 0
        }


def create_vector_database(db_type: str = 'memory', **config) -> VectorDatabase:
    """
    Factory function to create a vector database instance.
    
    Args:
        db_type: Type of database ('memory', 'pinecone', etc.)
        **config: Database-specific configuration
    
    Returns:
        VectorDatabase instance
    """
    if db_type == 'memory':
        return VectorDatabase()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


# Global in-memory database instance
_GLOBAL_DB = VectorDatabase()


def init_pinecone_idx():
    """
    Initialize vector database (compatibility function).
    Returns the global vector database instance.
    """
    global _GLOBAL_DB
    return _GLOBAL_DB


def store_embeddings(filename: str, db, embedding: List[float], namespace: str = None) -> None:
    """
    Store embeddings for a file (compatibility function).
    
    Args:
        filename: Name of the file
        db: Vector database instance
        embedding: Embedding vector
        namespace: Optional namespace
    """
    if db is None:
        db = _GLOBAL_DB
    
    metadata = {
        'filename': filename,
        'namespace': namespace
    }
    
    # Use filename as the ID
    file_id = f"{namespace}_{filename}" if namespace else filename
    db.store_embedding(file_id, embedding, metadata)


def semantic_search(query: str, db, voyage_client, top_k: int = 10, namespace: str = None) -> Dict:
    """
    Perform semantic search (compatibility function).
    
    Args:
        query: Search query
        db: Vector database instance
        voyage_client: Voyage AI client for embedding the query
        top_k: Number of results to return
        namespace: Optional namespace
    
    Returns:
        Dict with 'matches' list
    """
    if db is None:
        db = _GLOBAL_DB
    
    # Get query embedding
    try:
        from .embedding_engine import embed_query
        query_embedding = embed_query(query, voyage_client)
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return {'matches': []}
    
    # Search
    results = db.search(query_embedding, top_k, namespace)
    
    # Convert to expected format
    matches = []
    for result in results:
        matches.append({
            'id': result['id'],
            'score': result['similarity'],
            'metadata': result['metadata']
        })
    
    return {'matches': matches}



