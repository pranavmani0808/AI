import uuid
import re
from typing import List, Optional
from backend.rag.models import DocumentChunk
from backend.crawler.models import CrawledDocument
from backend.search.normalizer import normalize_url

def generate_deterministic_chunk_id(search_id: int, url: str, chunk_index: int, text: str) -> str:
    """
    Generates a deterministic UUID based on inputs to support idempotency.
    Utilizes uuid.uuid5 with the URL namespace.
    """
    norm_url = normalize_url(url)
    # Unique signature for this exact chunk
    signature = f"{search_id}_{norm_url}_{chunk_index}_{text.strip()}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, signature))

def split_into_sentences(text: str) -> List[str]:
    """Basic helper to segment paragraphs into sentences."""
    # Split on sentence ending characters followed by space or boundary
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    return [s.strip() for s in sentence_endings.split(text) if s.strip()]

def chunk_document(
    doc: CrawledDocument, 
    search_id: int, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200,
    subquery_id: Optional[int] = None
) -> List[DocumentChunk]:
    """
    Partitions CrawledDocument text body into overlapping semantic blocks:
    - Target character size is ~1000 characters, with ~200 characters overlap.
    - Preserves sentence boundaries (does not split sentences or words in half).
    - Preserves metadata mapping and maps to standard Pydantic DocumentChunk list.
    - Automatically skips chunks below minimum length (e.g. < 40 characters).
    """
    if not doc.text:
        return []
        
    url = doc.url
    title = doc.title or "Untitled Document"
    domain = url.split("//")[-1].split("/")[0]
    
    # 1. Split text into paragraphs
    paragraphs = [p.strip() for p in doc.text.split("\n\n") if p.strip()]
    
    chunks_text = []
    current_chunk = []
    current_length = 0
    
    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        
        # Scenario A: Paragraph fits in current chunk
        if current_length + (2 if current_chunk else 0) + paragraph_len <= chunk_size:
            current_chunk.append(paragraph)
            current_length += (2 if current_length > 0 else 0) + paragraph_len
        else:
            # Paragraph is too big for current chunk. Flush current chunk first if it has content
            if current_chunk:
                chunks_text.append("\n\n".join(current_chunk))
                # Set overlap. Keep last paragraph if within overlap boundary, else empty
                last_p = current_chunk[-1]
                if len(last_p) <= chunk_overlap:
                    current_chunk = [last_p]
                    current_length = len(last_p)
                else:
                    current_chunk = []
                    current_length = 0
            
            # Scenario B: Single paragraph is larger than chunk_size, split by sentences
            if paragraph_len > chunk_size:
                sentences = split_into_sentences(paragraph)
                for sentence in sentences:
                    sentence_len = len(sentence)
                    
                    if current_length + (1 if current_chunk else 0) + sentence_len <= chunk_size:
                        current_chunk.append(sentence)
                        current_length += (1 if current_length > 0 else 0) + sentence_len
                    else:
                        # Flush sentence-based chunk
                        if current_chunk:
                            chunks_text.append(" ".join(current_chunk))
                            # Apply overlap (keep last sentence if it is small enough)
                            last_s = current_chunk[-1]
                            if len(last_s) <= chunk_overlap:
                                current_chunk = [last_s]
                                current_length = len(last_s)
                            else:
                                current_chunk = []
                                current_length = 0
                                
                        # Handle long sentence edge case by itself
                        if sentence_len > chunk_size:
                            # Split by character segments safely
                            start = 0
                            while start < sentence_len:
                                end = start + chunk_size
                                char_slice = sentence[start:end]
                                chunks_text.append(char_slice)
                                start += chunk_size - chunk_overlap
                        else:
                            current_chunk.append(sentence)
                            current_length = sentence_len
            else:
                # Paragraph fits in a new chunk by itself
                current_chunk.append(paragraph)
                current_length = paragraph_len
                
    # Flush remaining chunk text
    if current_chunk:
        if current_length > 0:
            chunks_text.append("\n\n".join(current_chunk))
            
    # 2. Filter and wrap clean chunks into DocumentChunk objects
    document_chunks = []
    chunk_index = 0
    
    for text_block in chunks_text:
        text_strip = text_block.strip()
        # Skip small noise fragments (less than 40 chars or less than 8 words)
        if len(text_strip) < 40 or len(text_strip.split()) < 8:
            continue
            
        chunk_id = generate_deterministic_chunk_id(search_id, url, chunk_index, text_strip)
        word_count = len(text_strip.split())
        
        document_chunks.append(DocumentChunk(
            id=chunk_id,
            search_id=search_id,
            subquery_id=subquery_id,
            url=url,
            title=title,
            domain=domain,
            chunk_index=chunk_index,
            text=text_strip,
            word_count=word_count
        ))
        chunk_index += 1
        
    return document_chunks
