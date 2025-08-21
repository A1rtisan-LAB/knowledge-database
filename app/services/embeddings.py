"""Embeddings service for semantic search - Mock implementation for testing."""

import numpy as np
from typing import List, Tuple, Optional
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_embedding_model():
    """Get or initialize the embedding model - mock for testing."""
    logger.info("Mock: Using mock embedding model")
    return None


def chunk_text(text: str, max_length: int = 512) -> List[str]:
    """Split text into chunks for embedding."""
    if not text:
        return []
    
    # Simple chunking by sentences
    sentences = text.replace('\n\n', '. ').split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


async def generate_embeddings(item):
    """Generate embeddings for a knowledge item - mock for testing."""
    try:
        logger.info(f"Mock: Would generate embeddings for item {item.id if hasattr(item, 'id') else 'unknown'}")
        
        # Mock: generate random embeddings
        if hasattr(item, 'content_ko'):
            ko_chunks = chunk_text(item.content_ko)
            for i, chunk in enumerate(ko_chunks):
                embedding = np.random.randn(384).tolist()
                logger.debug(f"Mock: Generated Korean embedding for chunk {i}")
        
        if hasattr(item, 'content_en'):
            en_chunks = chunk_text(item.content_en)
            for i, chunk in enumerate(en_chunks):
                embedding = np.random.randn(384).tolist()
                logger.debug(f"Mock: Generated English embedding for chunk {i}")
                
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {str(e)}")


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    cosine_sim = dot_product / (norm1 * norm2)
    return float(cosine_sim)


async def find_similar_items(
    text: str,
    language: str = "en",
    limit: int = 10
) -> List[Tuple[str, float]]:
    """Find similar knowledge items based on text - mock for testing."""
    logger.info(f"Mock: Would find similar items for query: {text[:50]}...")
    return []