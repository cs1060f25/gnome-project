from typing import List, Optional
from PIL import Image
import voyageai


def embed_pdf_by_page(images: List[Image.Image], voyage_client: voyageai.Client) -> Optional[List[List[float]]]:
    """
    Generate embeddings for each PDF page image using Voyage AI.
    
    Args:
        images (List[Image.Image]): List of PIL Images, each representing a 
                                    page from a PDF document
        voyage_client (voyageai.Client): A Voyage AI client object
        
    Returns:
        List[List[float]]: Each image is embedded into a 1024-dimensional vector
        None: If API key is not found or if the embedding process fails
    """
    embeddings = []

    for img in images:

        # Get embedding for the image using voyage-3-multimodal model
        response = voyage_client.multimodal_embed(
            inputs=[[img]],
            model="voyage-multimodal-3",
            input_type="document"
        )
        
        # Extract embedding from the response
        embeddings.append(response.embeddings[0])
    
    return embeddings
