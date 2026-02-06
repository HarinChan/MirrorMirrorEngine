"""ChromaDB vector storage"""
from typing import List, Dict, Optional, Any
import uuid
import chromadb
from chromadb.api.types import Metadata



class ChromaDBService:
    """Service for managing document embeddings with ChromaDB"""
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "documents"):
        """
        Initialize ChromaDB client and collection
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.client: Any = chromadb.PersistentClient(path=persist_directory)
        self.collection_name: str = collection_name
        # Get or create collection with default embedding function
        self.collection: Any = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: List[str], metadatas: Optional[List[Metadata]] = None,
                      ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add documents to the ChromaDB collection
        
        Args:
            documents: List of text documents to embed and store
            metadatas: Optional list of metadata dictionaries for each document
            ids: Optional list of document IDs. If not provided, UUIDs will be generated
        
        Returns:
            Dictionary with status and document IDs
        """
        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]
            # Prepare metadatas if not provided
            if metadatas is None:
                metadatas = [{} for _ in documents]
            # Add to collection (ChromaDB will generate embeddings automatically)
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return {
                "status": "success",
                "message": f"Added {len(documents)} documents",
                "document_ids": ids
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def query_documents(self, query_text: str, n_results: int = 5,
                        where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query the ChromaDB collection for similar documents
        
        Args:
            query_text: The text query to search for
            n_results: Number of results to return
            where: Optional metadata filter
        
        Returns:
            Dictionary with query results
        """
        try:
            # Query the collection (ChromaDB will generate query embedding automatically)
            results: Any = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "similarity": 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            return {
                "status": "success",
                "query": query_text,
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def delete_documents(self, ids: List[str]) -> Dict[str, Any]:
        """
        Delete documents from the collection
        
        Args:
            ids: List of document IDs to delete
        
        Returns:
            Dictionary with status
        """
        try:
            self.collection.delete(ids=ids)
            return {
                "status": "success",
                "message": f"Deleted {len(ids)} documents",
                "deleted_ids": ids
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection
        
        Returns:
            Dictionary with collection information
        """
        try:
            count = self.collection.count()
            return {
                "status": "success",
                "collection_name": self.collection_name,
                "document_count": count
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def update_document(self, document_id: str, document: str,
                        metadata: Optional[Metadata] = None) -> Dict[str, Any]:
        """
        Update an existing document
        
        Args:
            document_id: ID of the document to update
            document: New document text
            metadata: Optional new metadata
        
        Returns:
            Dictionary with status
        """
        try:
            # Update the document (ChromaDB will generate new embedding automatically)
            update_kwargs = {
                "ids": [document_id],
                "documents": [document]
            }
            if metadata is not None:
                # metadata is guarded by the if-check above, so it's non-None here
                update_kwargs["metadatas"] = [metadata]  # type: ignore[assignment]
            self.collection.update(**update_kwargs)
            return {
                "status": "success",
                "message": f"Updated document {document_id}",
                "document_id": document_id
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
