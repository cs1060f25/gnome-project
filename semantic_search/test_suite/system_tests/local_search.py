from embedding_engine.voyage_client import init_voyage
from parsing_engine.parse_pdf import pdf_path_to_screenshots
from embedding_engine.embed_pdf import embed_pdf_by_page
from vector_database.store_vectors import store_embeddings
from vector_database.pinecone_client import init_pinecone_idx
from vector_database.semantic_search import semantic_search
import os

if __name__ == '__main__':

    namespace = "Local Test"

    # Set working directory to project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Config for upload - set to true, and set pdf path
    # Example: "pdf_path = "local_test_files/new_file.pdf""
    UPLOAD = True
    pdf_path = "local_test_files/voyage_multimodal_guide.pdf"

    # Config for search - set to true, and set query
    SEARCH = False
    query = "flag of england"
    
    # Initialize Voyage client
    voyage_client = init_voyage()
    if not voyage_client:
        print("Error: Failed to initialize Voyage client")
        exit(1)
    else:
        print("Voyage client initialized successfully")

    # Initialize Pinecone client
    pinecone_idx = init_pinecone_idx()
    if not pinecone_idx:
        print("Error: Failed to initialize Pinecone index")
        exit(1)
    else:
        print("Pinecone index initialized successfully")

    # Upload pipeline
    if UPLOAD:
        # Parse PDF
        screenshots = pdf_path_to_screenshots(pdf_path)
        if not screenshots:
            print("Error: Failed to parse PDF")
            exit(1)
        else:
            print("PDF parsed successfully")

        # Embed screenshots
        embeddings = embed_pdf_by_page(screenshots, voyage_client)
        if not embeddings:
            print("Error: Failed to generate embeddings for PDF")
            exit(1)
        else:
            print("Embeddings for PDF generated successfully")

        # Store embeddings
        num = store_embeddings(pdf_path, pdf_path, pinecone_idx, embeddings, namespace)
        if num == 0:
            print("Error: Failed to store embeddings in Pinecone")
            exit(1)
        else:
            print(f"{num} embeddings stored successfully")

    # Search pipeline
    if SEARCH:
        # Perform semantic search
        print(f"Query: {query}")
        results = semantic_search(query, pinecone_idx, voyage_client, 10, namespace=namespace)
        if not results:
            print("Error: Failed to perform semantic search")
            exit(1)
        else:
            print("Semantic search successful")
            for result in results:
                print("_" * 80)
                print(f"ID: {result['id']}")
                print(f"Score: {result['score']}")
                print(f"Filename: {result['metadata']['filename']}")