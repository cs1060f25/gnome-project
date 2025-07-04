from os import environ
import voyageai


def init_voyage():
    """
    Initialize the Voyage AI client.
    
    Returns:
        voyage_client: A Voyage AI client object
    """
    try:
        # Get API key from environment variable
        api_key = environ.get("VOYAGE_API_KEY")
        
        if not api_key:
            raise Exception("Setup: Missing Voyage API key.")
        
        # Initialize the Voyage AI client
        voyage_client = voyageai.Client(api_key=api_key)
        return voyage_client
        
    except Exception as e:
        raise Exception(f"Setup: Failed to initialize Voyage client: {str(e)}")