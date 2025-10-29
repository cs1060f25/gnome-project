# app.py - Enhanced Flask app with File Upload & Search UI
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuration
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}

# Create uploads directory
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Mocked users (in-memory for prototype - not production-safe)
users = {
    'test@example.com': generate_password_hash('password123')
}

# Mocked file storage (in-memory for prototype)
# In production, this would be a database
# Changed to dict with user email as key for proper file isolation
uploaded_files = {}  # Format: {user_email: [list of files]}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def mock_search(query, files):
    """
    Mock search function that performs simple keyword matching.
    In production, this would use semantic search with AI embeddings.
    """
    if not query:
        return files
    
    query_lower = query.lower()
    results = []
    
    for file in files:
        filename_lower = file['name'].lower()
        # Simple scoring based on keyword presence
        score = 0.0
        
        # Exact filename match gets highest score
        if query_lower == filename_lower:
            score = 1.0
        # Partial match in filename
        elif query_lower in filename_lower:
            score = 0.8
        # Word-level matching
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
    
    # Sort by score descending
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results


@app.route('/')
def index():
    """Serve Vue.js single-page application."""
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


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
        users[email] = password  # Add to mock dict
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/home')
def home():
    """Legacy route for compatibility."""
    if 'user' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# === API ENDPOINTS FOR FRONT-END ===

@app.route('/api/files')
def api_files():
    """API endpoint to get list of all uploaded files for the current user."""
    try:
        if 'user' not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_email = session['user']
        user_files = uploaded_files.get(user_email, [])
        
        return jsonify({
            "files": user_files,
            "syncStatus": {
                "Finder": {"status": "connected", "last_sync": datetime.now().isoformat()},
                "Google Drive": {"status": "disconnected"},
                "OneDrive": {"status": "disconnected"}
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Failed to fetch files: {e}")
        return jsonify({"files": [], "syncStatus": {}}), 500


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """API endpoint to handle file upload."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"}), 400
    
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save file
        save_path = app.config['UPLOAD_FOLDER'] / filename
        file.save(save_path)
        
        # Get file size
        file_size = os.path.getsize(save_path)
        
        # Add to current user's uploaded files list
        user_email = session['user']
        if user_email not in uploaded_files:
            uploaded_files[user_email] = []
        
        file_info = {
            "name": filename,
            "uploadDate": datetime.now().isoformat(),
            "source": "Finder",
            "size": file_size,
            "cloudUrl": None,
            "indexed": True,
            "file_path": str(save_path),
            "owner": user_email
        }
        uploaded_files[user_email].append(file_info)
        
        app.logger.info(f"File uploaded successfully: {filename} ({file_size} bytes) for user {user_email}")
        return jsonify({"message": f"Successfully uploaded {filename}"}), 200
        
    except Exception as exc:
        app.logger.error(f"Upload failed: {exc}")
        return jsonify({"error": f"Failed to process file: {exc}"}), 500


@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for file search (searches only current user's files)."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    query = data.get("query", "").strip() if data else ""
    
    if not query:
        return jsonify({"error": "Please enter a query"}), 400
    
    try:
        # Get current user's files only
        user_email = session['user']
        user_files = uploaded_files.get(user_email, [])
        
        # Perform mock search on user's files only
        results = mock_search(query, user_files)
        
        app.logger.info(f"Search '{query}' for user {user_email}: {len(results)} results found")
        
        return jsonify({"results": results[:15]}), 200
        
    except Exception as exc:
        app.logger.error(f"Search failed: {exc}")
        return jsonify({"error": f"Search failed: {exc}"}), 500


@app.route('/api/open-file/<filename>')
def api_open_file(filename):
    """Open a file (for local files, only user's own files)."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Get current user's files only
        user_email = session['user']
        user_files = uploaded_files.get(user_email, [])
        
        # Find file in user's uploaded files only
        file_info = next((f for f in user_files if f['name'] == filename), None)
        
        if not file_info:
            return jsonify({"error": "File not found"}), 404
        
        # Verify file belongs to current user
        if file_info.get('owner') != user_email:
            return jsonify({"error": "Unauthorized access"}), 403
        
        # For local files, return the file path
        # In production, this would open the file in the default application
        return jsonify({
            "message": "File found",
            "file_path": file_info.get('file_path')
        }), 200
        
    except Exception as exc:
        app.logger.error(f"Failed to open file: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route('/api/sync', methods=['POST'])
def api_sync():
    """API endpoint to trigger manual sync (stub for cloud integration)."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        source = data.get("source")
        
        # Stub implementation - would connect to cloud services
        return jsonify({
            "message": f"Sync triggered for {source if source else 'all sources'}",
            "results": {"status": "Cloud sync not yet implemented"}
        }), 200
        
    except Exception as exc:
        app.logger.error(f"Sync failed: {exc}")
        return jsonify({"error": f"Sync failed: {str(exc)}"}), 500


@app.route('/api/sync/status')
def api_sync_status():
    """Get sync status for all sources."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        status = {
            "Finder": {
                "status": "connected",
                "last_sync": datetime.now().isoformat(),
                "indexed_count": len([f for f in uploaded_files if f['source'] == 'Finder'])
            },
            "Google Drive": {
                "status": "disconnected",
                "indexed_count": 0
            },
            "OneDrive": {
                "status": "disconnected",
                "indexed_count": 0
            }
        }
        
        return jsonify({"status": status}), 200
        
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route('/api/connect/google-drive', methods=['POST'])
def api_connect_gdrive():
    """Stub for Google Drive OAuth connection (to be implemented in Feature 2)."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    return jsonify({
        "error": "Google Drive integration not yet implemented. This will be added in the Cloud Integration feature."
    }), 501


@app.route('/api/connect/onedrive', methods=['POST'])
def api_connect_onedrive():
    """Stub for OneDrive OAuth connection (to be implemented in Feature 2)."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    return jsonify({
        "error": "OneDrive integration not yet implemented. This will be added in the Cloud Integration feature."
    }), 501


@app.route('/api/disconnect/<source>', methods=['POST'])
def api_disconnect(source):
    """Stub for disconnecting cloud sources."""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    return jsonify({
        "message": f"{source} disconnect not yet implemented"
    }), 501


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

