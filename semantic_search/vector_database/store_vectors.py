from pinecone import Pinecone
from typing import List


def store_embeddings(file_id: str, file_name: str, pinecone_idx: Pinecone.Index, embeddings: List[List[float]], namespace: str) -> int:
    """
    Store embedded text chunks of a single file in Pinecone with metadata.
    
    Args:
        file_id (str): ID of the file
        file_name (str): Name of the file
        pinecone_idx (Pinecone.Index): A Pinecone index object
        embeddings (List[List[float]]): List of embedding vectors
        namespace (str): Namespace for the Pinecone storage index

    Returns:
        int: Number of vectors stored
    """
    if not file_id:
        print("Error: File ID not provided")
        return 0

    if not embeddings:
        print("Error: Embeddings empty")
        return 0

    if not pinecone_idx:
        print("Error: Pinecone index not initialized")
        return 0

    if not file_name:
        print("Error: File name not provided")
        return 0
    
    try:
        # Prepare the vectors for upsert
        vectors = []
        
        # Prepare vectors with IDs and metadata
        for i, embedding in enumerate(embeddings):
            # Check dimension
            if len(embedding) != 1024:
                print(f"Error: Vector {i} does not match dimension 1024")
                continue
                
            # Create a unique ID for this vector
            vector_id = f"page_{i}:{file_id}"
            
            metadata = {
                "filename": file_name,
                "file_id": file_id
            }
            
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            })
        
        # Upsert vectors
        pinecone_idx.upsert(vectors=vectors, namespace=namespace)
        return len(vectors)
    
    except Exception as e:
        print(f"Error: Failed to store embeddings in Pinecone: {str(e)}")
        return 0