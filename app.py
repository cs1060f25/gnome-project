# app.py - Full-featured Flask app with Semantic Search, Sync Engine, and User Auth
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import traceback
import sys
import secrets
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import socket
import requests
import json

# Ensure packages are importable
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import bundled config for API keys (optional)
try:
    from config.bundled_config import get_api_key
    USE_BUNDLED_CONFIG = True
    # Set environment variables from bundled config (if not already set)
    for key_name in ["VOYAGE_API_KEY", "PINECONE_API_KEY", "PINECONE_HOST", "COHERE_API_KEY"]:
        if not os.environ.get(key_name):
            bundled_value = get_api_key(key_name)
            if bundled_value:
                os.environ[key_name] = bundled_value
except ImportError:
    USE_BUNDLED_CONFIG = False

# Try to import semantic search components (optional - degrades gracefully)
SEMANTIC_SEARCH_ENABLED = False
try:
    from semantic.parsing_engine import parse_local_pdf
    from semantic.embedding_engine import init_voyage, embed_pdf
    from semantic.vector_database import init_pinecone_idx, store_embeddings, semantic_search
    from semantic.file_processor import process_file, is_supported_file
    from semantic.hybrid_search import hybrid_search_rerank, boost_exact_matches, filter_by_relevance
    SEMANTIC_SEARCH_ENABLED = True
except ImportError as e:
    print(f"Semantic search not available: {e}")
    # Define stub functions for graceful degradation
    def init_voyage(): return None
    def init_pinecone_idx(): return None

# Import database and sync engine
from database.models import GnomeDatabase

# Try to import sync engine (optional)
SYNC_ENGINE_ENABLED = False
try:
    from sync_engine.sync_manager import SyncManager
    SYNC_ENGINE_ENABLED = True
except ImportError as e:
    print(f"Sync engine not available: {e}")

# Flask setup
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = Path(__file__).resolve().parent / "uploads"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'pptx', 'xlsx'}
app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER: Path = app.config["UPLOAD_FOLDER"]
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize external clients
VOYAGE_CLIENT = init_voyage() if SEMANTIC_SEARCH_ENABLED else None
PINECONE_IDX = init_pinecone_idx() if SEMANTIC_SEARCH_ENABLED else None

# Generate unique namespace per user (based on machine UUID)
import uuid
import platform
import hashlib

def get_user_namespace():
    """Generate a unique namespace for this user's machine."""
    is_packaged = getattr(sys, 'frozen', False) or 'app.asar' in sys.argv[0] if sys.argv else False
    
    if not is_packaged:
        return "demo"  # Development mode
    
    machine_id = str(uuid.getnode())
    hostname = platform.node()
    namespace_string = f"{machine_id}_{hostname}"
    namespace_hash = hashlib.sha256(namespace_string.encode()).hexdigest()[:16]
    return f"user_{namespace_hash}"

NAMESPACE = get_user_namespace()

# Telemetry (optional)
def send_telemetry(event_name: str, properties: dict = None):
    """Send telemetry events (optional - requires Grafana setup)."""
    try:
        grafana_url = os.environ.get('GRAFANA_CLOUD_URL')
        grafana_key = os.environ.get('GRAFANA_CLOUD_API_KEY')
        
        if not grafana_url or not grafana_key:
            return
        
        timestamp_ns = int(datetime.now().timestamp() * 1e9)
        payload = {
            "streams": [{
                "stream": {"app": "gnome", "namespace": NAMESPACE, "event": event_name},
                "values": [[str(timestamp_ns), json.dumps({
                    "event": event_name,
                    "properties": properties or {},
                    "user_namespace": NAMESPACE
                })]]
            }]
        }
        
        requests.post(
            f"{grafana_url}/loki/api/v1/push",
            json=payload,
            headers={"Content-Type": "application/json"},
            auth=("", grafana_key),
            timeout=2
        )
    except Exception:
        pass

# Initialize database
DB = GnomeDatabase()

# Initialize sync manager if available
SYNC_MANAGER = None
if SYNC_ENGINE_ENABLED and VOYAGE_CLIENT and PINECONE_IDX:
    try:
        SYNC_MANAGER = SyncManager(DB, VOYAGE_CLIENT, PINECONE_IDX, NAMESPACE)
        SYNC_MANAGER.start_auto_sync()
    except Exception as e:
        print(f"Failed to initialize sync manager: {e}")

# Mocked users (in-memory for prototype)
users = {
    'test@example.com': generate_password_hash('password123')
}

# Mocked file storage for fallback
uploaded_files = {}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def mock_search(query, files):
    """Mock search for when semantic search is not available."""
    if not query:
        return files
    
    query_lower = query.lower()
    results = []
    
    for file in files:
        filename_lower = file['name'].lower()
        score = 0.0
        
        if query_lower == filename_lower:
            score = 1.0
        elif query_lower in filename_lower:
            score = 0.8
        else:
            query_words = set(query_lower.split())
            filename_words = set(filename_lower.replace('.', ' ').split())
            common_words = query_words.intersection(filename_words)
            if common_words:
                score = len(common_words) / len(query_words) * 0.6
        
        if score > 0:
            file_copy = file.copy()
            file_copy['similarity'] = score
            results.append(file_copy)
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results


# ============== ROUTES ==============

@app.route("/")
def index():
    """Serve Vue.js single-page application."""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Check if user has authorized (for Electron app)
    authorized_file = Path.home() / '.gnome' / 'authorized'
    if not authorized_file.exists() and SYNC_ENGINE_ENABLED:
        return render_template("welcome.html")
    
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect(url_for('index'))
        return 'Invalid credentials', 401
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))
        if email in users:
            return 'User exists', 409
        users[email] = password
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route("/api/authorize", methods=["POST"])
def api_authorize():
    """Mark user as having authorized file access."""
    try:
        authorized_file = Path.home() / '.gnome' / 'authorized'
        authorized_file.parent.mkdir(parents=True, exist_ok=True)
        authorized_file.write_text('authorized')
        return jsonify({"message": "Authorization saved"}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/files")
def api_files():
    """API endpoint to get list of all files."""
    try:
        if 'user' not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Try to get files from sync manager first
        if SYNC_MANAGER:
            db_files = SYNC_MANAGER.get_all_files()
            files = []
            for f in db_files:
                files.append({
                    "name": f['filename'],
                    "uploadDate": f.get('indexed_at'),
                    "source": f['source'],
                    "size": f.get('file_size'),
                    "cloudUrl": f.get('metadata', {}).get('webUrl') if isinstance(f.get('metadata'), dict) else None,
                    "indexed": True
                })
            sync_status = SYNC_MANAGER.get_sync_status()
        else:
            # Fallback to mock storage
            user_email = session['user']
            files = uploaded_files.get(user_email, [])
            sync_status = {
                "Finder": {"status": "connected", "last_sync": datetime.now().isoformat()},
                "Google Drive": {"status": "disconnected"},
                "OneDrive": {"status": "disconnected"}
            }
        
        files.sort(key=lambda x: x.get("uploadDate", ""), reverse=True)
        return jsonify({"files": files, "syncStatus": sync_status})
    except Exception as e:
        app.logger.error(f"Failed to fetch files: {e}")
        return jsonify({"files": [], "syncStatus": {}})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """API endpoint to handle file upload and processing."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(save_path)

    try:
        if SEMANTIC_SEARCH_ENABLED and VOYAGE_CLIENT and PINECONE_IDX:
            # Full semantic processing
            images = parse_local_pdf(str(save_path))
            embedding = embed_pdf(images, VOYAGE_CLIENT)
            store_embeddings(filename, PINECONE_IDX, embedding, NAMESPACE)
            
            # Store in database
            from database.models import compute_file_hash
            file_hash = compute_file_hash(str(save_path))
            DB.add_file(
                filename=filename,
                file_path=str(save_path),
                source='Finder',
                file_hash=file_hash,
                vector_id=f"upload_{file_hash[:16]}",
                file_size=os.path.getsize(save_path)
            )
        else:
            # Fallback to mock storage
            user_email = session['user']
            if user_email not in uploaded_files:
                uploaded_files[user_email] = []
            
            file_info = {
                "name": filename,
                "uploadDate": datetime.now().isoformat(),
                "source": "Finder",
                "size": os.path.getsize(save_path),
                "cloudUrl": None,
                "indexed": True,
                "file_path": str(save_path),
                "owner": user_email
            }
            uploaded_files[user_email].append(file_info)
        
        return jsonify({"message": f"Successfully uploaded and indexed {filename}"}), 200
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        app.logger.error("Upload failed:\n%s", traceback.format_exc())
        return jsonify({"error": f"Failed to process file: {exc}"}), 500


@app.route("/api/search", methods=["POST"])
def api_search():
    """API endpoint for hybrid semantic + keyword search."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    query = data.get("query", "").strip() if data else ""
    top_k = data.get("top_k", 30) if data else 30

    if not query:
        return jsonify({"error": "Please enter a query."}), 400

    try:
        if SEMANTIC_SEARCH_ENABLED and VOYAGE_CLIENT and PINECONE_IDX and SYNC_MANAGER:
            # Full semantic search
            response = semantic_search(query, PINECONE_IDX, VOYAGE_CLIENT, top_k, NAMESPACE)
            matches = response.get("matches", [])

            db_files = SYNC_MANAGER.get_all_files()
            db_files_dict = {f.get('pinecone_id') or f.get('vector_id'): f for f in db_files}
            
            results = []
            for match in matches:
                match_id = match.get("id", "")
                metadata = match.get("metadata", {})
                
                db_file = db_files_dict.get(match_id)
                
                if db_file:
                    metadata = db_file.get('metadata', {})
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    cloud_url = metadata.get('webUrl') or metadata.get('webViewLink')
                    if not cloud_url and db_file['source'] == 'Google Drive':
                        cloud_url = f"https://drive.google.com/file/d/{db_file['file_path']}/view"
                    
                    result = {
                        "name": db_file['filename'],
                        "similarity": match.get("score", 0),
                        "source": db_file['source'],
                        "cloudUrl": cloud_url,
                        "file_path": db_file['file_path'],
                        "uploadDate": db_file.get('indexed_at'),
                        "indexed": True
                    }
                else:
                    result = {
                        "name": metadata.get("filename", match_id),
                        "similarity": match.get("score", 0),
                        "source": metadata.get("source", "Unknown"),
                        "cloudUrl": metadata.get('webUrl'),
                        "file_path": metadata.get('file_path'),
                        "uploadDate": None,
                        "indexed": True
                    }
                
                results.append(result)
            
            # Apply hybrid reranking
            results = hybrid_search_rerank(query, results, semantic_weight=0.4, keyword_weight=0.6)
            results = boost_exact_matches(query, results, boost_factor=0.35)
            results = filter_by_relevance(results, min_score=0.05)
            results = results[:10]

            send_telemetry("search_performed", {
                "query_length": len(query),
                "results_count": len(results),
                "top_score": results[0]['similarity'] if results else 0
            })
            
            return jsonify({"results": results}), 200
        else:
            # Fallback to mock search
            user_email = session['user']
            user_files = uploaded_files.get(user_email, [])
            results = mock_search(query, user_files)
            return jsonify({"results": results[:15]}), 200
        
    except Exception as exc:
        app.logger.error("Search failed:\n%s", traceback.format_exc())
        return jsonify({"error": f"Search failed: {exc}"}), 500


@app.route("/api/sync", methods=["POST"])
def api_sync():
    """API endpoint to trigger manual sync."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        source = data.get("source")
        
        if SYNC_MANAGER:
            if source:
                result = SYNC_MANAGER.sync_source(source)
                return jsonify({"message": f"Synced {source}", "result": result}), 200
            else:
                results = SYNC_MANAGER.sync_all()
                return jsonify({"message": "Synced all sources", "results": results}), 200
        else:
            return jsonify({"message": "Sync not available (sync engine not initialized)"}), 200
    except Exception as exc:
        app.logger.error(f"Sync failed: {exc}")
        return jsonify({"error": f"Sync failed: {str(exc)}"}), 500


@app.route("/api/sync/status")
def api_sync_status():
    """Get sync status for all sources."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        if SYNC_MANAGER:
            status = SYNC_MANAGER.get_sync_status()
            for source in ['Finder', 'Google Drive', 'OneDrive']:
                indexed_count = len(SYNC_MANAGER.get_files_by_source(source))
                if source in status:
                    status[source]['indexed_count'] = indexed_count
        else:
            status = {
                "Finder": {"status": "connected", "indexed_count": 0},
                "Google Drive": {"status": "disconnected", "indexed_count": 0},
                "OneDrive": {"status": "disconnected", "indexed_count": 0}
            }
        
        return jsonify({"status": status}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/connect/google-drive", methods=["POST"])
def api_connect_gdrive():
    """Initiate Google Drive OAuth connection."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not SYNC_MANAGER:
        return jsonify({"error": "Sync engine not available"}), 501
    
    try:
        data = request.get_json(silent=True) or {}
        user_provided_email = data.get('email', 'Not provided')
        
        success = SYNC_MANAGER.connect_google_drive()
        
        if success:
            send_telemetry("google_drive_connected", {})
            return jsonify({"message": "Google Drive connected successfully! Syncing files..."}), 200
        else:
            return jsonify({"error": "Failed to connect Google Drive"}), 500
            
    except Exception as exc:
        app.logger.error(f"Google Drive connection failed: {exc}")
        if "access_denied" in str(exc).lower():
            return jsonify({"error": "Access denied - test user approval required", "code": "access_denied"}), 403
        return jsonify({"error": f"Connection error: {str(exc)}"}), 500


@app.route("/api/connect/onedrive", methods=["POST"])
def api_connect_onedrive():
    """Initiate OneDrive OAuth connection."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not SYNC_MANAGER:
        return jsonify({"error": "Sync engine not available"}), 501
    
    try:
        if not os.environ.get('MICROSOFT_CLIENT_ID') or not os.environ.get('MICROSOFT_CLIENT_SECRET'):
            return jsonify({"error": "OneDrive OAuth not configured"}), 400
        
        success = SYNC_MANAGER.connect_onedrive()
        if success:
            return jsonify({"message": "OneDrive connected successfully! Syncing files..."}), 200
        else:
            return jsonify({"error": "Failed to connect OneDrive"}), 500
    except Exception as exc:
        app.logger.error(f"OneDrive connection failed: {exc}")
        return jsonify({"error": f"Connection error: {str(exc)}"}), 500


@app.route("/api/disconnect/<source>", methods=["POST"])
def api_disconnect(source):
    """Disconnect a cloud source."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        if SYNC_MANAGER:
            SYNC_MANAGER.disconnect_source(source)
            return jsonify({"message": f"{source} disconnected"}), 200
        else:
            return jsonify({"message": f"{source} disconnect not available"}), 501
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/open-file/<filename>")
def api_open_file(filename):
    """Open a file in appropriate app."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        source = request.args.get('source')
        
        if SYNC_MANAGER:
            files = SYNC_MANAGER.get_all_files()
            if source:
                file_info = next((f for f in files if f['filename'] == filename and f['source'] == source), None)
            else:
                file_info = next((f for f in files if f['filename'] == filename), None)
        else:
            user_email = session['user']
            user_files = uploaded_files.get(user_email, [])
            file_info = next((f for f in user_files if f['name'] == filename), None)
        
        if not file_info:
            return jsonify({"error": "File not found"}), 404
        
        file_source = file_info.get('source', 'Finder')
        
        if file_source == 'Finder':
            import subprocess
            file_path = file_info.get('file_path')
            if file_path:
                subprocess.run(['open', file_path], check=True)
            return jsonify({"message": "File opened in Finder"}), 200
            
        elif file_source == 'Google Drive':
            import webbrowser
            metadata = file_info.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            url = metadata.get('webUrl') or metadata.get('webViewLink')
            if not url:
                url = f"https://drive.google.com/file/d/{file_info.get('file_path')}/view"
            
            webbrowser.open(url, new=2)
            return jsonify({"message": "File opened in browser"}), 200
        else:
            return jsonify({"error": "Unsupported source"}), 400
            
    except Exception as exc:
        app.logger.error(f"Failed to open file: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/debug/env")
def api_debug_env():
    """Debug endpoint to check environment variables."""
    return jsonify({
        "VOYAGE_API_KEY": "set" if os.environ.get('VOYAGE_API_KEY') else "missing",
        "PINECONE_API_KEY": "set" if os.environ.get('PINECONE_API_KEY') else "missing",
        "SEMANTIC_SEARCH_ENABLED": SEMANTIC_SEARCH_ENABLED,
        "SYNC_ENGINE_ENABLED": SYNC_ENGINE_ENABLED,
        "USE_BUNDLED_CONFIG": USE_BUNDLED_CONFIG
    })


if __name__ == "__main__":
    debug_mode = '--debug' in sys.argv
    
    try:
        app.run(debug=debug_mode, host="0.0.0.0", port=5001)
    finally:
        if SYNC_MANAGER:
            SYNC_MANAGER.stop_auto_sync()
        DB.close()
