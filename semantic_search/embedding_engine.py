from typing import List
from PIL import Image
from voyageai import Client
from os import environ


def init_voyage() -> Client:
    """
    Initialize the Voyage AI client.
    
    Returns:
        voyage_client: A Voyage AI client object.
    """
    try:
        api_key = environ.get("VOYAGE_API_KEY")
        
        if not api_key:
            raise ValueError("Voyage API key was not found.")
        
        voyage_client = Client(api_key=api_key)
        return voyage_client
        
    except Exception as e:
        raise Exception(f"Failed to initialize Voyage client: {str(e)}.")


def embed_pdf(images: List[Image.Image], voyage_client: Client) -> List[float]:
    """
    Generate embeddings a PDF document using Voyage AI.
    
    Args:
        images (List[Image.Image]): List of PIL Images, each representing a 
                                    page from a PDF document.
        voyage_client (Client): A Voyage AI client object.
        
    Returns:
        List[float]: Each document is embedded into a 1024-dimensional
                     vector.
    """
    if not images:
        raise ValueError("No PDF page images were found.")
    if not voyage_client:
        raise ValueError("No Voyage AI client was provided.")
    if not isinstance(images, list):
        raise TypeError("PDF images must be a list of PIL images.")
    if not all(isinstance(img, Image.Image) for img in images):
        raise TypeError("All images must be PIL Images.")
    if not isinstance(voyage_client, Client):
        raise ValueError("Voyage client is not the correct object type.")

    try:
        response = voyage_client.multimodal_embed(
            inputs=[images],
            model="voyage-multimodal-3",
            input_type="document"
        ).embeddings[0]
    except Exception as e:
        raise Exception(f"Failed to generate embeddings for PDF: {str(e)}.")
    
    return response


def embed_query(query: str, voyage_client: Client) -> List[float]:
    """
    Generate embeddings for a search query using Voyage AI.
    
    Args:
        query (str): The search query to generate embeddings for.
        voyage_client (Client): A Voyage AI client object.
        
    Returns:
        List[float]: Embedded 1024-dimensional vector of the query.
    """
    if not query:
        raise ValueError("No query was provided.")
    if not voyage_client:
        raise ValueError("No Voyage AI client was provided.")
    if not isinstance(query, str):
        raise ValueError("Query must be a string.")
    if not isinstance(voyage_client, Client):
        raise ValueError("Voyage client is not the correct object type.")

    try:
        response = voyage_client.multimodal_embed(
            model="voyage-multimodal-3",
            inputs=[[query]],
            input_type="query"
        ).embeddings[0]
    except Exception as e:
        raise Exception(f"Failed to generate embeddings for query: {str(e)}.")
    
    return response