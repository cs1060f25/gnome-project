# Semantic Search Module

This module implements AI embeddings and semantic search capabilities for the Gnome file management platform.

## Features

- **Multi-format File Processing**: Support for PDF, images, Word docs, PowerPoint, Excel, and text files
- **Advanced Search Algorithms**: 
  - BM25 scoring for keyword relevance
  - Query expansion with synonyms
  - Hybrid search combining semantic + keyword matching
  - Multi-signal reranking (semantic, keyword, recency, file type)
- **Vector Database**: Generic interface for vector storage (in-memory by default)
- **Embedding Engine**: Flexible embedding generation (works with any embedding service)

## Architecture

### Core Components

1. **`advanced_search.py`**: Advanced reranking with BM25, query expansion, and multi-signal scoring
2. **`hybrid_search.py`**: Hybrid semantic + keyword search
3. **`embedding_engine.py`**: Generic embedding generation interface
4. **`file_processor.py`**: Multi-format file processing and text extraction
5. **`parsing_engine.py`**: PDF to image conversion
6. **`vector_database.py`**: Generic vector storage and similarity search

## Usage

### Basic Search

```python
from semantic.advanced_search import advanced_search
from semantic.hybrid_search import hybrid_search_rerank

# Simple hybrid search
results = hybrid_search_rerank(query="resume", results=file_list)

# Advanced search with reranking
results = advanced_search(query="tax documents", results=file_list, full_corpus=all_files)
```

### File Processing

```python
from semantic.file_processor import process_file, is_supported_file

# Check if file is supported
if is_supported_file("document.pdf"):
    # Process file and get embeddings
    embeddings = process_file("document.pdf", embedding_client)
```

### Vector Database

```python
from semantic.vector_database import VectorDatabase

# Create in-memory vector database
db = VectorDatabase()

# Store embeddings
db.store_embedding(file_id="doc1", embedding=vector, metadata={"name": "resume.pdf"})

# Search
results = db.search(query_embedding=query_vector, top_k=10)
```

## Configuration

### Without External Services

The module can run entirely in-memory without any external API keys:

- **Vector Storage**: Uses in-memory cosine similarity search
- **Keyword Search**: BM25 and hybrid search work without embeddings
- **File Processing**: Text extraction works locally

### With Embedding Services (Optional)

To use semantic embeddings, configure an embedding client:

```python
# Example with Voyage AI (or use any embedding service)
from voyageai import Client

embedding_client = Client(api_key="your-api-key")
```

## Dependencies

Required:
- `PyMuPDF` - PDF processing
- `Pillow` - Image processing

Optional:
- `pytesseract` - OCR for images
- `python-docx` - Word document support
- `python-pptx` - PowerPoint support
- `openpyxl` - Excel support
- `voyageai` - Voyage AI embeddings (or use alternative)

## File Format Support

- **PDF**: Multimodal processing (converts to images)
- **Images**: PNG, JPG, JPEG (with OCR if available)
- **Documents**: DOCX
- **Presentations**: PPTX
- **Spreadsheets**: XLSX, CSV
- **Text**: TXT, MD, RTF

## Search Scoring

The advanced search uses multi-signal scoring:

| Signal | Weight | Purpose |
|--------|--------|---------|
| Semantic | 25% | Meaning-based similarity |
| BM25 | 25% | Keyword relevance |
| Exact Match | 40% | Filename matching (highest priority) |
| Recency | 8% | Favor recent files |
| File Type | 2% | Match file type to query |

## Implementation Notes

- **No Pinecone Required**: This version uses in-memory vector storage by default
- **No API Keys Required**: Can run entirely locally for keyword search
- **Extensible**: Easy to integrate with any embedding service or vector database
- **Production Ready**: Includes error handling, logging, and comprehensive file type support

## Integration with Gnome

This module is designed to replace the basic keyword search in `app.py` with advanced semantic search capabilities. See the integration examples in the tests folder.

## HW8 Feature Implementation

**Ticket**: Implement AI embeddings and core semantic search  
**Estimate**: 40 hours  
**Status**: Core implementation complete

### Subtasks Completed:
- ✅ Text extraction libraries and model setup
- ✅ Batch embedding generation pipeline
- ✅ Vector storage and basic similarity search
- ✅ Accuracy tuning and error handling

