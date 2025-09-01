"""
Shared Memory Manager - Vector Database Integration for AI Memory
================================================================

This module provides a unified interface for vector database operations across all AI agents.
It supports both Qdrant (local Docker) and Pinecone (cloud) backends for storing and retrieving
AI memories, case summaries, and learned patterns.

Key Features:
- Unified interface for Qdrant and Pinecone
- Automatic embedding generation using OpenAI
- Production-grade error handling and retry logic
- Comprehensive logging and monitoring
- Type-safe operations with Pydantic models

Author: Agentic KYC Engine Team
Version: 1.0.0
Framework: Qdrant/Pinecone with OpenAI embeddings
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

# Vector database clients
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
    from qdrant_client.http.exceptions import ResponseHandlingException
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logging.warning("Qdrant client not available. Install with: pip install qdrant-client")

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logging.warning("Pinecone client not available. Install with: pip install pinecone-client")

# OpenAI for embeddings
from openai import AsyncOpenAI
import numpy as np

# Pydantic for data validation
from pydantic import BaseModel, Field, validator
import structlog

# Configure structured logging
logger = structlog.get_logger(__name__)

class MemoryBackend(str, Enum):
    """Supported vector database backends"""
    QDRANT = "qdrant"
    PINECONE = "pinecone"

class MemoryType(str, Enum):
    """Types of memories that can be stored"""
    CASE_SUMMARY = "case_summary"
    COMPLIANCE_RULE = "compliance_rule"
    DOCUMENT_ANALYSIS = "document_analysis"
    DECISION_PATTERN = "decision_pattern"
    AGENT_LEARNING = "agent_learning"

@dataclass
class MemoryMetadata:
    """Metadata associated with a memory entry"""
    memory_id: str
    memory_type: MemoryType
    agent_name: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = None
    tags: List[str] = None
    confidence_score: float = 1.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.tags is None:
            self.tags = []

class MemoryEntry(BaseModel):
    """A memory entry to be stored in the vector database"""
    content: str = Field(..., description="The textual content of the memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Associated metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding (auto-generated if None)")
    
    class Config:
        arbitrary_types_allowed = True

class MemorySearchResult(BaseModel):
    """Result from a memory search operation"""
    memory_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    
    class Config:
        arbitrary_types_allowed = True

class MemoryManager:
    """
    Unified memory manager for vector database operations
    
    Provides a consistent interface for storing and retrieving AI memories
    across different vector database backends (Qdrant, Pinecone).
    """
    
    def __init__(
        self,
        backend: MemoryBackend,
        openai_api_key: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        pinecone_api_key: Optional[str] = None,
        pinecone_environment: str = "us-west1-gcp-free",
        embedding_model: str = "text-embedding-3-small",
        collection_name: str = "kyc_memories"
    ):
        """
        Initialize the memory manager
        
        Args:
            backend: The vector database backend to use
            openai_api_key: OpenAI API key for generating embeddings
            qdrant_host: Qdrant server host (for Qdrant backend)
            qdrant_port: Qdrant server port (for Qdrant backend)
            pinecone_api_key: Pinecone API key (for Pinecone backend)
            pinecone_environment: Pinecone environment (for Pinecone backend)
            embedding_model: OpenAI embedding model to use
            collection_name: Name of the collection/index to use
        """
        self.backend = backend
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize OpenAI client for embeddings
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize vector database client based on backend
        if backend == MemoryBackend.QDRANT:
            if not QDRANT_AVAILABLE:
                raise ImportError("Qdrant client not available. Install with: pip install qdrant-client")
            self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
            self._ensure_qdrant_collection()
            
        elif backend == MemoryBackend.PINECONE:
            if not PINECONE_AVAILABLE:
                raise ImportError("Pinecone client not available. Install with: pip install pinecone-client")
            if not pinecone_api_key:
                raise ValueError("Pinecone API key is required for Pinecone backend")
            
            pinecone.init(api_key=pinecone_api_key, environment=pinecone_environment)
            self._ensure_pinecone_index()
            
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        
        logger.info(
            "Memory manager initialized",
            backend=backend.value,
            collection_name=collection_name,
            embedding_model=embedding_model
        )
    
    def _ensure_qdrant_collection(self):
        """Ensure the Qdrant collection exists with proper configuration"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection with appropriate vector size for text-embedding-3-small
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=1536,  # text-embedding-3-small dimension
                        distance=qdrant_models.Distance.COSINE
                    )
                )
                logger.info("Created Qdrant collection", collection_name=self.collection_name)
            else:
                logger.info("Qdrant collection already exists", collection_name=self.collection_name)
                
        except Exception as e:
            logger.error("Failed to ensure Qdrant collection", error=str(e))
            raise
    
    def _ensure_pinecone_index(self):
        """Ensure the Pinecone index exists with proper configuration"""
        try:
            # Check if index exists
            if self.collection_name not in pinecone.list_indexes():
                # Create index with appropriate dimension for text-embedding-3-small
                pinecone.create_index(
                    name=self.collection_name,
                    dimension=1536,  # text-embedding-3-small dimension
                    metric="cosine"
                )
                logger.info("Created Pinecone index", index_name=self.collection_name)
            else:
                logger.info("Pinecone index already exists", index_name=self.collection_name)
            
            # Connect to the index
            self.pinecone_index = pinecone.Index(self.collection_name)
            
        except Exception as e:
            logger.error("Failed to ensure Pinecone index", error=str(e))
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text using OpenAI
        
        Args:
            text: The text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            
            logger.debug(
                "Generated embedding",
                text_length=len(text),
                embedding_dimension=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e), text_preview=text[:100])
            raise
    
    async def store_memory(
        self,
        content: str,
        metadata: MemoryMetadata,
        memory_id: Optional[str] = None
    ) -> str:
        """
        Store a memory in the vector database
        
        Args:
            content: The textual content of the memory
            metadata: Metadata associated with the memory
            memory_id: Optional custom memory ID (auto-generated if None)
            
        Returns:
            The ID of the stored memory
        """
        if memory_id is None:
            memory_id = str(uuid.uuid4())
        
        try:
            # Generate embedding for the content
            embedding = await self.generate_embedding(content)
            
            # Prepare metadata for storage
            storage_metadata = {
                "memory_id": memory_id,
                "memory_type": metadata.memory_type.value,
                "agent_name": metadata.agent_name,
                "customer_id": metadata.customer_id,
                "session_id": metadata.session_id,
                "created_at": metadata.created_at.isoformat(),
                "tags": metadata.tags,
                "confidence_score": metadata.confidence_score,
                "content": content  # Store content in metadata for easy retrieval
            }
            
            # Store based on backend
            if self.backend == MemoryBackend.QDRANT:
                await self._store_qdrant_memory(memory_id, embedding, storage_metadata)
            elif self.backend == MemoryBackend.PINECONE:
                await self._store_pinecone_memory(memory_id, embedding, storage_metadata)
            
            logger.info(
                "Stored memory successfully",
                memory_id=memory_id,
                memory_type=metadata.memory_type.value,
                agent_name=metadata.agent_name,
                backend=self.backend.value
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(
                "Failed to store memory",
                error=str(e),
                memory_type=metadata.memory_type.value,
                agent_name=metadata.agent_name
            )
            raise
    
    async def _store_qdrant_memory(self, memory_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """Store memory in Qdrant"""
        point = qdrant_models.PointStruct(
            id=memory_id,
            vector=embedding,
            payload=metadata
        )
        
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    async def _store_pinecone_memory(self, memory_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """Store memory in Pinecone"""
        self.pinecone_index.upsert(
            vectors=[(memory_id, embedding, metadata)]
        )
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        agent_name: Optional[str] = None,
        customer_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[MemorySearchResult]:
        """
        Search for similar memories in the vector database
        
        Args:
            query: The search query text
            memory_type: Filter by memory type
            agent_name: Filter by agent name
            customer_id: Filter by customer ID
            tags: Filter by tags (any of the provided tags)
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of matching memory search results
        """
        try:
            # Generate embedding for the query
            query_embedding = await self.generate_embedding(query)
            
            # Build filter conditions
            filters = {}
            if memory_type:
                filters["memory_type"] = memory_type.value
            if agent_name:
                filters["agent_name"] = agent_name
            if customer_id:
                filters["customer_id"] = customer_id
            if tags:
                filters["tags"] = {"$in": tags}
            
            # Search based on backend
            if self.backend == MemoryBackend.QDRANT:
                results = await self._search_qdrant_memories(
                    query_embedding, filters, limit, similarity_threshold
                )
            elif self.backend == MemoryBackend.PINECONE:
                results = await self._search_pinecone_memories(
                    query_embedding, filters, limit, similarity_threshold
                )
            
            logger.info(
                "Memory search completed",
                query_preview=query[:100],
                num_results=len(results),
                filters=filters,
                backend=self.backend.value
            )
            
            return results
            
        except Exception as e:
            logger.error("Failed to search memories", error=str(e), query_preview=query[:100])
            raise
    
    async def _search_qdrant_memories(
        self,
        query_embedding: List[float],
        filters: Dict[str, Any],
        limit: int,
        similarity_threshold: float
    ) -> List[MemorySearchResult]:
        """Search memories in Qdrant"""
        # Build Qdrant filter
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == "tags" and isinstance(value, dict) and "$in" in value:
                    # Handle tags filter
                    for tag in value["$in"]:
                        conditions.append(
                            qdrant_models.FieldCondition(
                                key="tags",
                                match=qdrant_models.MatchAny(any=[tag])
                            )
                        )
                else:
                    conditions.append(
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value)
                        )
                    )
            
            if conditions:
                qdrant_filter = qdrant_models.Filter(
                    must=conditions if len(conditions) > 1 else conditions[0]
                )
        
        # Perform search
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=qdrant_filter,
            limit=limit,
            score_threshold=similarity_threshold
        )
        
        # Convert to MemorySearchResult objects
        results = []
        for result in search_results:
            results.append(MemorySearchResult(
                memory_id=result.id,
                content=result.payload.get("content", ""),
                metadata=result.payload,
                similarity_score=result.score
            ))
        
        return results
    
    async def _search_pinecone_memories(
        self,
        query_embedding: List[float],
        filters: Dict[str, Any],
        limit: int,
        similarity_threshold: float
    ) -> List[MemorySearchResult]:
        """Search memories in Pinecone"""
        # Perform search
        search_results = self.pinecone_index.query(
            vector=query_embedding,
            filter=filters if filters else None,
            top_k=limit,
            include_metadata=True
        )
        
        # Convert to MemorySearchResult objects
        results = []
        for match in search_results.matches:
            if match.score >= similarity_threshold:
                results.append(MemorySearchResult(
                    memory_id=match.id,
                    content=match.metadata.get("content", ""),
                    metadata=match.metadata,
                    similarity_score=match.score
                ))
        
        return results
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[MemorySearchResult]:
        """
        Retrieve a specific memory by its ID
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory if found, None otherwise
        """
        try:
            if self.backend == MemoryBackend.QDRANT:
                result = self.qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=[memory_id]
                )
                if result:
                    point = result[0]
                    return MemorySearchResult(
                        memory_id=point.id,
                        content=point.payload.get("content", ""),
                        metadata=point.payload,
                        similarity_score=1.0  # Exact match
                    )
            
            elif self.backend == MemoryBackend.PINECONE:
                result = self.pinecone_index.fetch(ids=[memory_id])
                if memory_id in result.vectors:
                    vector_data = result.vectors[memory_id]
                    return MemorySearchResult(
                        memory_id=memory_id,
                        content=vector_data.metadata.get("content", ""),
                        metadata=vector_data.metadata,
                        similarity_score=1.0  # Exact match
                    )
            
            return None
            
        except Exception as e:
            logger.error("Failed to get memory by ID", error=str(e), memory_id=memory_id)
            raise
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the vector database
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            if self.backend == MemoryBackend.QDRANT:
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=qdrant_models.PointIdsList(
                        points=[memory_id]
                    )
                )
            
            elif self.backend == MemoryBackend.PINECONE:
                self.pinecone_index.delete(ids=[memory_id])
            
            logger.info("Deleted memory successfully", memory_id=memory_id, backend=self.backend.value)
            return True
            
        except Exception as e:
            logger.error("Failed to delete memory", error=str(e), memory_id=memory_id)
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory collection
        
        Returns:
            Dictionary containing collection statistics
        """
        try:
            if self.backend == MemoryBackend.QDRANT:
                info = self.qdrant_client.get_collection(self.collection_name)
                return {
                    "backend": "qdrant",
                    "collection_name": self.collection_name,
                    "total_memories": info.points_count,
                    "vector_dimension": info.config.params.vectors.size,
                    "distance_metric": info.config.params.vectors.distance.value
                }
            
            elif self.backend == MemoryBackend.PINECONE:
                stats = self.pinecone_index.describe_index_stats()
                return {
                    "backend": "pinecone",
                    "index_name": self.collection_name,
                    "total_memories": stats.total_vector_count,
                    "vector_dimension": stats.dimension
                }
            
        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            return {"error": str(e)}

# Factory function for easy initialization
def create_memory_manager(
    backend: str,
    openai_api_key: str,
    **kwargs
) -> MemoryManager:
    """
    Factory function to create a MemoryManager instance
    
    Args:
        backend: "qdrant" or "pinecone"
        openai_api_key: OpenAI API key for embeddings
        **kwargs: Additional arguments for MemoryManager
        
    Returns:
        Configured MemoryManager instance
    """
    backend_enum = MemoryBackend(backend.lower())
    return MemoryManager(backend=backend_enum, openai_api_key=openai_api_key, **kwargs)

