from pinecone import Pinecone
from voyageai import Client
from typing import Optional, List, Dict, Any

from embedding_engine.embed_query import embed_query


def semantic_search(query: str, pinecone_idx: Pinecone.Index, voyage_client: Client, top_k: int, namespace: str) -> Optional[List[Dict[str, Any]]]:
    """
    Perform semantic search in Pinecone using Voyage AI Embedding Engine.
    
    Args:
        query (str): The search query
        pinecone_idx (Pinecone.Index): A Pinecone index object
        voyage_client (Client): A Voyage AI client object
        top_k (int): Number of vectors to fetch
        namespace (str): Namespace to search in
        
    Returns:
        List[Dict[str, Any]]: List of matches with id, score, and metadata,
                              filtered to include only the highest scoring
                              chunk from each unique file
    """
    
    # Generate embedding for the query
    query_embedding = embed_query(query, voyage_client)
    
    if not query_embedding:
        raise Exception("Error: Failed to generate embeddings for query")

    # Query Pinecone
    query_response = pinecone_idx.query(
        namespace=namespace,
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    # Extract all matches
    all_matches = []
    if hasattr(query_response, 'matches'):
        for match in query_response.matches:
            all_matches.append({
                'id': match.id,
                'score': match.score,
                'metadata': match.metadata
            })
    
    # Filter to keep only the highest scoring chunk from each file
    present_file_names = set()
    filtered_matches = []
    for match in all_matches:
        # Extract filename from metadata
        file_name = match['metadata'].get('filename', '')
        
        if file_name not in present_file_names:
            filtered_matches.append(match)
            present_file_names.add(file_name)
    
    # Limit to the requested top_k
    if len(filtered_matches) > top_k:
        filtered_matches = filtered_matches[:top_k]
    
    return filtered_matches
