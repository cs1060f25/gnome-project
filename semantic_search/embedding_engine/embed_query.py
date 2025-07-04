from typing import Optional, List
from voyageai import Client


def embed_query(query: str, voyage_client: Client) -> Optional[List[float]]:
    """
    Generate embeddings for a search query using Voyage AI.
    
    Args:
        query (str): The search query to generate embeddings for
        voyage_client (voyageai.Client): A Voyage AI client object
        
    Returns:
        List[float]: Embedded 1024-dimensional vector of the query
        None: If API key is not found or if the embedding process fails
    """
    # Get 1024-dimensional embeddings using the voyage-multimodal-3 model
    response = voyage_client.multimodal_embed(
        model="voyage-multimodal-3",
        inputs=[[query]],
        input_type="query"
    )
    
    # Extract embeddings from the response
    embedding = response.embeddings[0]
    
    return embedding
