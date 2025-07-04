# Dependencies
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from os import environ
from json import loads
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Packages
from google_drive_helpers.download_file import download_file
from parsing_engine.parse_pdf import bytesio_to_screenshots
from embedding_engine.embed_pdf import embed_pdf_by_page
from embedding_engine.voyage_client import init_voyage
from vector_database.store_vectors import store_embeddings
from vector_database.pinecone_client import init_pinecone_idx
from vector_database.semantic_search import semantic_search

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize Firestore database
db = None

def get_firestore_db():
    global db

    if db is None:
        # Get the Firebase credentials from the environment variable
        firebase_credentials = environ.get("FIREBASE_CREDENTIALS")

        if firebase_credentials is None:
            logging.exception("Setup: FIREBASE_CREDENTIALS environment variable is not set.")
            raise Exception("Setup: FIREBASE_CREDENTIALS environment variable is not set.")
        
        try:
            cred_info = loads(firebase_credentials)
            cred = credentials.Certificate(cred_info)
            initialize_app(cred)
            db = firestore.client()
        except Exception as e:
            logging.exception(f"Setup: Failed to initialize Firestore: {str(e)}")
            raise

    return db

# Initialize Pinecone client
pinecone_idx = None

def get_pinecone_idx():
    global pinecone_idx

    if pinecone_idx is None:
        try:
            pinecone_idx = init_pinecone_idx()
        except Exception as e:
            logging.exception(f"Setup: Failed to initialize Pinecone client: {str(e)}")
            raise

    return pinecone_idx

# Initialize Voyage client
voyage_client = None

def get_voyage_client():
    global voyage_client

    if voyage_client is None:
        try:
            voyage_client = init_voyage()
        except Exception as e:
            logging.exception(f"Setup: Failed to initialize Voyage client: {str(e)}")
            raise

    return voyage_client

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route("/google-drive/store-token", methods=["POST"])
def store_user_token():
    try:
        # Get posted data
        data = request.get_json()
        user_id = data.get("user_id")
        token = data.get("token")

        if not user_id or not token:
            logging.error("/store-user-token: Missing user_id or token.")
            return jsonify({"error": "Missing user_id or token."}), 400

        # Get user's Firestore document reference
        db = get_firestore_db()
        doc_ref = db.collection('user_tokens').document(user_id)

        # Save the user's token.json
        doc_ref.set({
            "token": token,
        })

        return jsonify({"status": "Successfully stored user token."}), 200
    except Exception as e:
        logging.exception(f"/store-user-token: Failed to store user token: {str(e)}")
        return jsonify({"error": "Internal server error."}), 500

@app.route("/google-drive/file-upload", methods=["POST"])
def file_upload():
    try:
        # Get posted data
        data = request.get_json()
        user_id = data.get("user_id")
        file_id = data.get("file_id")
        
        if not user_id or not file_id:
            logging.error("/file-upload: Missing user_id or file_id.")
            return jsonify({"error": "Missing user_id or file_id."}), 400

        # Fetch token.json from Firestore for this user
        db = get_firestore_db()
        doc_ref = db.collection('user_tokens').document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            user_data = doc.to_dict()
            user_token = user_data.get("token")
        else:
            logging.error(f"/file-upload: file id: {file_id} - User token not found.")
            return jsonify({"error": "User token not found"}), 404

        # Refresh token if expired
        creds = Credentials.from_authorized_user_info(user_token)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                user_token = loads(creds.to_json())
                doc_ref.set({"token": user_token})
            except Exception as e:
                logging.error(f"/file-upload: file id: {file_id} - Token refresh failed: {str(e)}")
                return jsonify({"error": "Token refresh failed"}), 401
            
        # Download file
        file_bytes, file_name = download_file(file_id, user_token)

        if not file_bytes or not file_name:
            logging.error(f"/file-upload: file id: {file_id} - Failed to download file.")
            return jsonify({"error": "Failed to download file"}), 500
        
        # Parse file
        screenshots = bytesio_to_screenshots(file_bytes)

        if not screenshots:
            logging.error(f"/file-upload: file id: {file_id} - Failed to parse file.")
            return jsonify({"error": "Failed to parse file"}), 500

        # Embed screenshots
        voyage_client = get_voyage_client()
        embeddings = embed_pdf_by_page(screenshots, voyage_client)

        if not embeddings:
            logging.error(f"/file-upload: file id: {file_id} - Failed to generate embeddings.")
            return jsonify({"error": "Failed to generate embeddings"}), 500

        # Store embeddings
        pinecone_idx = get_pinecone_idx()
        num = store_embeddings(file_id, file_name, pinecone_idx, embeddings, user_id)

        if num == 0:
            logging.error(f"/file-upload: file id: {file_id} - Failed to store embeddings in Pinecone.")
            return jsonify({"error": "Failed to store embeddings in Pinecone"}), 500
            
        return jsonify({"status": "File upload pipeline was successful"}), 200
    except Exception as e:
        logging.error(f"/file-upload: file id: {file_id} - Failed to complete file upload pipeline: {str(e)}")
        return jsonify({"error": "Internal server error."}), 500

@app.route("/google-drive/file-search", methods=["POST"])
def file_search():
    try:
        # Get posted data
        data = request.get_json()
        query = data.get("query")
        user_id = data.get("user_id")
        
        if not query or not user_id:
            return jsonify({"error": "Missing query or user_id"}), 400

        # Perform semantic search
        pinecone_idx = get_pinecone_idx()
        voyage_client = get_voyage_client()
        results = semantic_search(query, pinecone_idx, voyage_client, 10, namespace=user_id)

        if not results:
            logging.error(f"/file-search: user_id: {user_id}, query: {query} - Failed to perform semantic search.")
            return jsonify({"error": "We found no matches for this query"}), 500

        return jsonify({"results": results}), 200
    except Exception as e:
        logging.error(f"/file-search: user_id: {user_id}, query: {query} - Failed to complete file search pipeline: {str(e)}")
        return jsonify({"error": "Internal server error."}), 500
