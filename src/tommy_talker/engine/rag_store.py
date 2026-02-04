"""
TommyTalker RAG Store
ChromaDB operations for vector storage with session hygiene (wipe capability).
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import uuid

# ChromaDB import
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("[WARNING] chromadb not installed - RAG features disabled")


@dataclass
class Document:
    """A document stored in the RAG system."""
    id: str
    content: str
    metadata: dict
    

@dataclass
class SearchResult:
    """Result from a RAG search."""
    documents: list[Document]
    distances: list[float]


class RAGStore:
    """
    ChromaDB-based vector store for RAG operations.
    
    Features:
    - Session-based collections
    - Full session wipe for hygiene
    - Semantic search on transcripts
    """
    
    DEFAULT_COLLECTION = "transcripts"
    
    def __init__(self, db_path: Path):
        """
        Initialize RAG store.
        
        Args:
            db_path: Path to ChromaDB storage directory
        """
        self.db_path = db_path
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        
        if not HAS_CHROMADB:
            print("[RAGStore] ChromaDB not available")
            return
            
        self._initialize()
        
    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        if not HAS_CHROMADB:
            return
            
        try:
            # Ensure directory exists
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False  # Privacy-first
                )
            )
            
            # Get or create default collection
            self._collection = self._client.get_or_create_collection(
                name=self.DEFAULT_COLLECTION,
                metadata={"description": "TommyTalker transcripts"}
            )
            
            print(f"[RAGStore] Initialized at: {self.db_path}")
            print(f"[RAGStore] Collection '{self.DEFAULT_COLLECTION}' has {self._collection.count()} documents")
            
        except Exception as e:
            print(f"[RAGStore] Error initializing: {e}")
            
    def add_transcript(self, text: str, metadata: Optional[dict] = None) -> Optional[str]:
        """
        Add a transcript to the store.
        
        Args:
            text: Transcript text
            metadata: Optional metadata (mode, timestamp, speakers, etc.)
            
        Returns:
            Document ID or None if failed
        """
        if not self._collection:
            return None
            
        try:
            doc_id = str(uuid.uuid4())
            
            self._collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata or {}]
            )
            
            print(f"[RAGStore] Added document: {doc_id[:8]}...")
            return doc_id
            
        except Exception as e:
            print(f"[RAGStore] Error adding transcript: {e}")
            return None
            
    def search(self, query: str, n_results: int = 5) -> Optional[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            n_results: Maximum number of results
            
        Returns:
            SearchResult or None if failed
        """
        if not self._collection:
            return None
            
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                documents.append(Document(
                    id=doc_id,
                    content=results.get("documents", [[]])[0][i],
                    metadata=results.get("metadatas", [[]])[0][i]
                ))
                
            distances = results.get("distances", [[]])[0]
            
            return SearchResult(
                documents=documents,
                distances=distances
            )
            
        except Exception as e:
            print(f"[RAGStore] Error searching: {e}")
            return None
            
    def clear_session(self) -> bool:
        """
        Clear all documents from the store.
        
        SESSION HYGIENE: This wipes the vector store to prevent
        data bleeding between interviews/sessions.
        
        Returns:
            True if cleared successfully
        """
        if not self._client:
            return False
            
        try:
            # Delete and recreate collection
            self._client.delete_collection(self.DEFAULT_COLLECTION)
            
            self._collection = self._client.create_collection(
                name=self.DEFAULT_COLLECTION,
                metadata={"description": "TommyTalker transcripts"}
            )
            
            print("[RAGStore] Session cleared - all documents wiped")
            return True
            
        except Exception as e:
            print(f"[RAGStore] Error clearing session: {e}")
            return False
            
    def get_document_count(self) -> int:
        """Get the number of documents in the store."""
        if not self._collection:
            return 0
        return self._collection.count()
        
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a specific document.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted successfully
        """
        if not self._collection:
            return False
            
        try:
            self._collection.delete(ids=[doc_id])
            print(f"[RAGStore] Deleted document: {doc_id[:8]}...")
            return True
        except Exception as e:
            print(f"[RAGStore] Error deleting document: {e}")
            return False
