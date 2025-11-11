"""
AI-powered file auto-organization with clustering and tagging suggestions.
Implements CS1060-160: As a user, I can auto-organize files with AI suggestions.
"""
from typing import List, Dict, Tuple, Optional
import logging
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    Auto-organize files using AI embeddings and clustering.
    Generates suggestions for renaming and tagging files.
    """
    
    def __init__(self, vector_database, embedding_client=None):
        """
        Initialize the file organizer.
        
        Args:
            vector_database: VectorDatabase instance for retrieving embeddings
            embedding_client: Optional embedding client for generating new embeddings
        """
        self.vector_db = vector_database
        self.embedding_client = embedding_client
    
    def cluster_files(self, file_ids: List[str], threshold: float = 0.7) -> List[List[str]]:
        """
        Cluster files based on embedding similarity using simple threshold-based clustering.
        
        Args:
            file_ids: List of file IDs to cluster
            threshold: Similarity threshold for grouping (0.0-1.0)
        
        Returns:
            List of clusters, where each cluster is a list of file IDs
        """
        if not file_ids:
            return []
        
        # Get all embeddings
        file_embeddings = {}
        for file_id in file_ids:
            if file_id in self.vector_db.vectors:
                file_embeddings[file_id] = self.vector_db.vectors[file_id]['embedding']
        
        if not file_embeddings:
            logger.warning("No embeddings found for provided file IDs")
            return [[fid] for fid in file_ids]  # Each file in its own cluster
        
        # Simple greedy clustering algorithm
        clusters = []
        processed = set()
        
        for file_id in file_ids:
            if file_id in processed or file_id not in file_embeddings:
                continue
            
            # Start a new cluster
            cluster = [file_id]
            processed.add(file_id)
            embedding1 = file_embeddings[file_id]
            
            # Find similar files
            for other_id in file_ids:
                if other_id in processed or other_id not in file_embeddings:
                    continue
                
                embedding2 = file_embeddings[other_id]
                similarity = self.vector_db._cosine_similarity(embedding1, embedding2)
                
                if similarity >= threshold:
                    cluster.append(other_id)
                    processed.add(other_id)
            
            clusters.append(cluster)
        
        # Add unprocessed files (no embeddings) as individual clusters
        for file_id in file_ids:
            if file_id not in processed:
                clusters.append([file_id])
        
        logger.info(f"Clustered {len(file_ids)} files into {len(clusters)} groups")
        return clusters
    
    def suggest_tags(self, cluster: List[str]) -> List[str]:
        """
        Suggest tags for a cluster of similar files using zero-shot classification.
        
        Args:
            cluster: List of file IDs in the cluster
        
        Returns:
            List of suggested tags
        """
        if not cluster:
            return []
        
        # Extract common patterns from filenames
        filenames = []
        for file_id in cluster:
            if file_id in self.vector_db.vectors:
                metadata = self.vector_db.vectors[file_id].get('metadata', {})
                filename = metadata.get('name', metadata.get('filename', file_id))
                filenames.append(filename)
        
        if not filenames:
            return []
        
        # Extract common words and patterns
        tags = self._extract_common_patterns(filenames)
        
        # Predefined category tags based on content patterns
        category_tags = self._classify_file_categories(filenames)
        
        # Combine and return unique tags
        all_tags = list(set(tags + category_tags))
        return all_tags[:5]  # Limit to top 5 tags
    
    def suggest_folder_name(self, cluster: List[str]) -> str:
        """
        Suggest a folder name for organizing a cluster of files.
        
        Args:
            cluster: List of file IDs in the cluster
        
        Returns:
            Suggested folder name
        """
        tags = self.suggest_tags(cluster)
        
        if tags:
            # Use the most common/descriptive tag
            return tags[0].replace('_', ' ').title()
        
        # Fallback: use common prefix from filenames
        filenames = []
        for file_id in cluster:
            if file_id in self.vector_db.vectors:
                metadata = self.vector_db.vectors[file_id].get('metadata', {})
                filename = metadata.get('name', metadata.get('filename', file_id))
                filenames.append(filename)
        
        if filenames:
            common_prefix = self._find_common_prefix(filenames)
            if common_prefix and len(common_prefix) > 3:
                return common_prefix.replace('_', ' ').replace('-', ' ').title()
        
        return f"Group_{len(cluster)}_files"
    
    def generate_organization_suggestions(self, user_files: List[Dict]) -> List[Dict]:
        """
        Generate complete organization suggestions for a user's files.
        
        Args:
            user_files: List of file dictionaries with 'name' and other metadata
        
        Returns:
            List of organization suggestions with actions
        """
        if not user_files:
            return []
        
        # Extract file IDs (use 'name' as ID for now)
        file_ids = [f.get('name', f.get('filename', str(i))) for i, f in enumerate(user_files)]
        
        # Store embeddings if not already present (mock for now)
        for i, file_info in enumerate(user_files):
            file_id = file_ids[i]
            if file_id not in self.vector_db.vectors:
                # Create mock embedding based on filename
                mock_embedding = self._generate_mock_embedding(file_info.get('name', ''))
                self.vector_db.store_embedding(
                    file_id,
                    mock_embedding,
                    metadata=file_info
                )
        
        # Cluster files
        clusters = self.cluster_files(file_ids, threshold=0.6)
        
        # Generate suggestions
        suggestions = []
        for idx, cluster in enumerate(clusters):
            if len(cluster) < 2:
                # Skip single-file clusters (no organization needed)
                continue
            
            tags = self.suggest_tags(cluster)
            folder_name = self.suggest_folder_name(cluster)
            
            # Get file details
            files_in_cluster = []
            for file_id in cluster:
                if file_id in self.vector_db.vectors:
                    metadata = self.vector_db.vectors[file_id]['metadata']
                    files_in_cluster.append({
                        'name': metadata.get('name', file_id),
                        'size': metadata.get('size', 0),
                        'source': metadata.get('source', 'Unknown')
                    })
            
            suggestion = {
                'id': f'suggestion_{idx}',
                'type': 'organize',
                'action': 'move_to_folder',
                'folder_name': folder_name,
                'tags': tags,
                'files': files_in_cluster,
                'confidence': self._calculate_cluster_confidence(cluster),
                'description': f"Organize {len(cluster)} similar files into '{folder_name}'"
            }
            
            suggestions.append(suggestion)
        
        logger.info(f"Generated {len(suggestions)} organization suggestions")
        return suggestions
    
    def _extract_common_patterns(self, filenames: List[str]) -> List[str]:
        """Extract common patterns and keywords from filenames."""
        # Remove extensions
        names = [name.rsplit('.', 1)[0] for name in filenames]
        
        # Split into words
        all_words = []
        for name in names:
            # Split on common delimiters
            words = re.split(r'[_\-\s.]+', name.lower())
            all_words.extend(words)
        
        # Count word frequency
        word_counts = defaultdict(int)
        for word in all_words:
            if len(word) > 2:  # Skip very short words
                word_counts[word] += 1
        
        # Return words that appear in multiple files
        common_threshold = max(2, len(filenames) * 0.3)
        common_words = [
            word for word, count in word_counts.items()
            if count >= common_threshold
        ]
        
        return sorted(common_words, key=lambda w: word_counts[w], reverse=True)
    
    def _classify_file_categories(self, filenames: List[str]) -> List[str]:
        """Classify files into predefined categories based on patterns."""
        categories = []
        
        # Check for common patterns
        patterns = {
            'invoice': ['invoice', 'bill', 'receipt'],
            'contract': ['contract', 'agreement', 'terms'],
            'report': ['report', 'analysis', 'summary'],
            'presentation': ['presentation', 'slides', 'deck'],
            'financial': ['financial', 'budget', 'expense'],
            'legal': ['legal', 'law', 'court'],
            'tax': ['tax', 'irs', '1099', 'w2'],
            'client': ['client', 'customer'],
            'project': ['project', 'proj'],
            'meeting': ['meeting', 'notes', 'minutes'],
        }
        
        all_filenames = ' '.join(filenames).lower()
        
        for category, keywords in patterns.items():
            if any(keyword in all_filenames for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find common prefix among strings."""
        if not strings:
            return ""
        
        # Sort strings to compare first and last
        sorted_strings = sorted(strings)
        first = sorted_strings[0]
        last = sorted_strings[-1]
        
        # Find common prefix
        prefix = []
        for i, char in enumerate(first):
            if i < len(last) and char == last[i]:
                prefix.append(char)
            else:
                break
        
        prefix_str = ''.join(prefix).strip('_- ')
        return prefix_str
    
    def _calculate_cluster_confidence(self, cluster: List[str]) -> float:
        """
        Calculate confidence score for a cluster suggestion.
        
        Args:
            cluster: List of file IDs in the cluster
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if len(cluster) < 2:
            return 0.0
        
        # Calculate average pairwise similarity
        embeddings = []
        for file_id in cluster:
            if file_id in self.vector_db.vectors:
                embeddings.append(self.vector_db.vectors[file_id]['embedding'])
        
        if len(embeddings) < 2:
            return 0.5  # Medium confidence if no embeddings
        
        # Calculate average similarity
        total_similarity = 0.0
        count = 0
        
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = self.vector_db._cosine_similarity(embeddings[i], embeddings[j])
                total_similarity += similarity
                count += 1
        
        avg_similarity = total_similarity / count if count > 0 else 0.0
        
        # Boost confidence for larger clusters
        size_boost = min(0.2, len(cluster) * 0.05)
        confidence = min(1.0, avg_similarity + size_boost)
        
        return round(confidence, 2)
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate a simple mock embedding based on text hash.
        In production, this would use the actual embedding client.
        
        Args:
            text: Text to generate embedding for
        
        Returns:
            Mock embedding vector (128 dimensions)
        """
        # Simple hash-based mock embedding
        import hashlib
        
        # Create a deterministic embedding based on text
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector (128 dimensions)
        embedding = []
        for i in range(128):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1]
            embedding.append((byte_val / 127.5) - 1.0)
        
        # Add some variation based on common words
        common_words = ['invoice', 'report', 'contract', 'tax', 'legal', 'client', 'project']
        text_lower = text.lower()
        for idx, word in enumerate(common_words):
            if word in text_lower:
                # Boost certain dimensions for similar documents
                for i in range(10):
                    dim = (idx * 10 + i) % 128
                    embedding[dim] = embedding[dim] * 0.5 + 0.5
        
        return embedding


def rename_file_with_suggestions(original_name: str, tags: List[str]) -> str:
    """
    Generate a suggested new filename based on tags.
    
    Args:
        original_name: Original filename
        tags: Suggested tags for the file
    
    Returns:
        Suggested new filename
    """
    # Extract extension
    parts = original_name.rsplit('.', 1)
    name = parts[0]
    extension = parts[1] if len(parts) > 1 else ''
    
    # Clean up original name
    cleaned_name = re.sub(r'[^\w\s-]', '', name)
    cleaned_name = re.sub(r'[-_\s]+', '_', cleaned_name).strip('_')
    
    # Add primary tag if useful
    if tags and tags[0].lower() not in cleaned_name.lower():
        new_name = f"{tags[0]}_{cleaned_name}"
    else:
        new_name = cleaned_name
    
    # Reconstruct with extension
    if extension:
        return f"{new_name}.{extension}"
    return new_name

