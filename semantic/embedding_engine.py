"""
Embedding engine for generating vector embeddings from text and files.
Note: This module can work with any embedding service. Configure your client separately.
"""
from typing import List, Optional
from PIL import Image


def embed_pdf(images: List[Image.Image], embedding_client) -> List[float]:
    """
    Generate embeddings for a PDF document.
    
    Args:
        images (List[Image.Image]): List of PIL Images, each representing a 
                                    page from a PDF document.
        embedding_client: Client object for embedding generation
        
    Returns:
        List[float]: Document embedding vector
    """
    if not images:
        raise ValueError("No PDF page images were found.")
    if not embedding_client:
        raise ValueError("No embedding client was provided.")
    if not isinstance(images, list):
        raise TypeError("PDF images must be a list of PIL images.")
    if not all(isinstance(img, Image.Image) for img in images):
        raise TypeError("All images must be PIL Images.")

    try:
        # This is a generic interface - adapt based on your embedding service
        if hasattr(embedding_client, 'multimodal_embed'):
            # Voyage AI style
            response = embedding_client.multimodal_embed(
                inputs=[images],
                model="voyage-multimodal-3",
                input_type="document"
            ).embeddings[0]
        else:
            raise ValueError("Embedding client does not support multimodal embedding")
        
        return response
    except Exception as e:
        raise Exception(f"Failed to generate embeddings for PDF: {str(e)}.")


def embed_query(query: str, embedding_client) -> List[float]:
    """
    Generate embeddings for a search query.
    
    Args:
        query (str): The search query to generate embeddings for.
        embedding_client: Client object for embedding generation
        
    Returns:
        List[float]: Embedded vector of the query.
    """
    if not query:
        raise ValueError("No query was provided.")
    if not embedding_client:
        raise ValueError("No embedding client was provided.")
    if not isinstance(query, str):
        raise ValueError("Query must be a string.")

    try:
        # Generic interface - adapt based on your embedding service
        if hasattr(embedding_client, 'multimodal_embed'):
            # Voyage AI style
            response = embedding_client.multimodal_embed(
                model="voyage-multimodal-3",
                inputs=[[query]],
                input_type="query"
            ).embeddings[0]
        elif hasattr(embedding_client, 'embed'):
            # Simple text embedding style
            response = embedding_client.embed(
                texts=[query],
                model="voyage-3",
                input_type="query"
            ).embeddings[0]
        else:
            raise ValueError("Embedding client does not support query embedding")
        
        return response
    except Exception as e:
        raise Exception(f"Failed to generate embeddings for query: {str(e)}.")


def embed_text(text: str, embedding_client) -> List[float]:
    """
    Embed text using the provided embedding client.
    
    Args:
        text: Text to embed (will be truncated if too long)
        embedding_client: Client object for embedding generation
    
    Returns:
        Embedding vector
    """
    if not text:
        raise ValueError("No text was provided.")
    if not embedding_client:
        raise ValueError("No embedding client was provided.")
    
    # Truncate if needed (conservative limit)
    MAX_CHARS = 32000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
    
    try:
        if hasattr(embedding_client, 'embed'):
            response = embedding_client.embed(
                texts=[text],
                model="voyage-3",
                input_type="document"
            )
            return response.embeddings[0]
        else:
            raise ValueError("Embedding client does not support text embedding")
    except Exception as e:
        raise Exception(f"Failed to embed text: {str(e)}.")

