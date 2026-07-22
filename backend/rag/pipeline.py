import time
from typing import List, Dict, Any, Tuple, Optional
from backend.crawler.models import CrawledDocument
from backend.rag.models import DocumentChunk, RetrievedChunk, RetrievalResponse
from backend.rag.cleaner import clean_extracted_text
from backend.rag.chunker import chunk_document
from backend.rag.embeddings import embed_texts
from backend.rag.vector_store import upsert_chunks
from backend.rag.retriever import retrieve_evidence

async def run_indexing_pipeline(
    crawled_documents: List[CrawledDocument], 
    search_id: int, 
    subquery_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Cleans, chunks, embeds, and indexes crawled documents into Qdrant in batch mode.
    Returns metrics statistics dictionary.
    """
    start_time = time.time()
    
    chunks_created: List[DocumentChunk] = []
    documents_processed = 0
    failed_documents = 0
    
    for doc in crawled_documents:
        if doc.crawl_status != "SUCCESS" or not doc.text:
            failed_documents += 1
            continue
            
        try:
            # 1. Clean the plain text
            clean_text = clean_extracted_text(doc.text)
            # Create a temporary modified doc copy to pass to chunker
            temp_doc = doc.model_copy(update={"text": clean_text})
            
            # 2. Split into overlapping paragraph chunks
            doc_chunks = chunk_document(temp_doc, search_id, subquery_id=subquery_id)
            chunks_created.extend(doc_chunks)
            documents_processed += 1
        except Exception as e:
            print(f"Document processing failed for {doc.url}: {e}")
            failed_documents += 1
            
    # 3. Generate and upsert embeddings if chunks exist
    chunks_indexed = 0
    if chunks_created:
        try:
            chunk_texts = [chunk.text for chunk in chunks_created]
            print(f"Generating batch embeddings for {len(chunk_texts)} chunks...")
            vectors = embed_texts(chunk_texts)
            
            if vectors and len(vectors) == len(chunks_created):
                print(f"Upserting vectors into Qdrant collection...")
                upsert_chunks(chunks_created, vectors)
                chunks_indexed = len(chunks_created)
            else:
                print("Failed to map embeddings correctly. Vectors count mismatch.")
        except Exception as e:
            print(f"RAG indexing pipeline execution failed: {e}")
            
    duration_ms = int((time.time() - start_time) * 1000)
    
    return {
        "documents_processed": documents_processed,
        "chunks_created": len(chunks_created),
        "chunks_indexed": chunks_indexed,
        "failed_documents": failed_documents,
        "duration_ms": duration_ms
    }

async def run_retrieval_pipeline(query: str, search_id: int, top_k: int = 8) -> List[RetrievedChunk]:
    """
    Retrieves matching evidence contexts for a search session.
    """
    return await retrieve_evidence(query, search_id, top_k=top_k)
