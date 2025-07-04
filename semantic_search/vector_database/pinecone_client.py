from pinecone import Pinecone
from os import environ


def init_pinecone_idx():
    """
    Initialize the Pinecone client and connect to the index.
    
    Returns:
        Pinecone.Index: A Pinecone index object
    """
    try:
        # Get environment variables
        api_key = environ.get("PINECONE_API_KEY")
        host = environ.get("PINECONE_HOST")
        
        if not api_key or not host:
            raise Exception("Setup: Missing Pinecone credentials.")
        
        # Initialize Pinecone
        pc = Pinecone(api_key=api_key)
        index = pc.Index(host=host)
        return index
    
    except Exception as e:
        raise Exception(f"Setup: Failed to initialize Pinecone client: {str(e)}")