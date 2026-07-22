from typing import List, Optional
from backend.core.config import settings

_model = None

def get_embedding_model():
    """
    Lazy-loads the embedding model sentence-transformers/all-MiniLM-L6-v2 on CPU.
    Thread-safe and caches it globally so it only initializes once per process.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = settings.EMBEDDING_MODEL
        print(f"Loading embedding model '{model_name}' on CPU...")
        try:
            # Force CPU model mapping to avoid CUDA/MPS context switches or dependencies
            _model = SentenceTransformer(model_name, device="cpu")
            print("Embedding model initialized successfully.")
        except Exception as e:
            print(f"Failed to load sentence-transformers model {model_name}: {e}")
            raise e
    return _model

def embed_text(text: str) -> List[float]:
    """
    Generates a single normalized 384-dimensional vector embedding.
    """
    if not text:
        return []
    try:
        model = get_embedding_model()
        # normalize_embeddings=True enforces L2 unit length normalization for cosine comparisons
        vector = model.encode(text.strip(), normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        print(f"Failed to generate embedding for text: {e}")
        return []

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generates batch normalized embeddings for a list of text blocks.
    """
    if not texts:
        return []
    try:
        model = get_embedding_model()
        cleaned_texts = [t.strip() for t in texts if t.strip()]
        if not cleaned_texts:
            return []
        vectors = model.encode(cleaned_texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()
    except Exception as e:
        print(f"Failed to generate batch embeddings: {e}")
        return []
