from pathlib import Path
from typing import List
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
import os
import logging
import traceback
import sys
import secrets

# Ensure semantic_search package is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from semantic_search.parsing_engine import parse_local_pdf
from semantic_search.embedding_engine import init_voyage, embed_pdf
from semantic_search.vector_database import (
    init_pinecone_idx,
    store_embeddings,
    semantic_search,
)

# Flask setup
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = (
    Path(__file__).resolve().parent / "uploads"
)
app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER: Path = app.config["UPLOAD_FOLDER"]
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize external clients once
VOYAGE_CLIENT = init_voyage()
PINECONE_IDX = init_pinecone_idx()
NAMESPACE = "demo"


@app.route("/")
def index():
    """Home page: upload form & list of uploaded files."""
    files: List[str] = [f.name for f in UPLOAD_FOLDER.glob("*.pdf")]
    return render_template("index.html", files=files)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle PDF upload and pipeline processing."""
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("index"))
    save_path = UPLOAD_FOLDER / file.filename
    file.save(save_path)

    try:
        # Parse PDF into images
        images = parse_local_pdf(str(save_path))
        # Embed images
        embedding = embed_pdf(images, VOYAGE_CLIENT)
        # Store embeddings in Pinecone
        store_embeddings(file.filename, PINECONE_IDX, embedding, NAMESPACE)
        flash(f"Uploaded and indexed {file.filename} ")
    except Exception as exc:  # pylint: disable=broad-except
        save_path.unlink(missing_ok=True)
        app.logger.error("Upload failed:\n%s", traceback.format_exc())
        flash(f"Failed to process file: {exc}")

    return redirect(url_for("index"))


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search page with results."""
    results = []
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        top_k_raw = request.form.get("top_k", "5")

        if not query:
            flash("Please enter a query.")
        else:
            try:
                top_k = int(top_k_raw)
                response = semantic_search(
                    query, PINECONE_IDX, VOYAGE_CLIENT, top_k, NAMESPACE
                )
                # Pinecone returns dict with "matches"
                results = response.get("matches", [])
            except ValueError:
                flash("top_k must be an integer.")
            except Exception as exc:  # pylint: disable=broad-except
                flash(f"Search failed: {exc}")

    return render_template("search.html", results=results)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)