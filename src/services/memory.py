from typing import Dict, List, Optional
from sentence_transformers import SentenceTransformer
import google.genai as genai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.models import SourceDocument, ContentChunk, Concept, Relationship
from configuration.configuration import Configuration as Config, logger


def store_relationship(concept1: str, concept2: str, relation_type: str = "related_to"):
    c1 = Concept.objects(name=concept1).first()
    c2 = Concept.objects(name=concept2).first()
    if c1 and c2:
        rel = Relationship(
            concept1_id=c1.id,
            concept2_id=c2.id,
            relation_type=relation_type,
        )
        rel.save()
        logger.info(f"Stored relationship: {concept1} -> {concept2} ({relation_type})")


def get_document_by_id(doc_id: str) -> Optional[SourceDocument]:
    return SourceDocument.objects(id=doc_id).first()


class AgentMemory:
    def __init__(self, config: Config):
        self.config = config
        self.embedding_model = SentenceTransformer(config.embedding_model)

        if not self.config.gemini_api_key:
            raise ValueError("❌ Missing GEMINI_API_KEY. Please set it in your .env")

        self.gemini_client = genai.Client(api_key=self.config.gemini_api_key)
        logger.info("✅ Gemini client initialized")

        # Initialize memory statistics
        self.stats = {
            "documents_stored": 0,
            "chunks_created": 0,
            "concepts_extracted": 0,
            "relationships_mapped": 0
        }

    def store_document(self, document: SourceDocument) -> None:
        """Store document with semantic chunking and concept extraction"""
        try:
            if not self.check_duplicate(document):
                document.save()
                self._create_and_store_chunks(document)
                self.stats["documents_stored"] += 1
                logger.info(f"✅ Document stored: {document.title} ({document.id})")
            else:
                logger.info(f"⚠️ Duplicate document skipped: {document.title}")
        except Exception as e:
            logger.error(f"Error storing document {document.id}: {e}")
            raise

    def _create_and_store_chunks(self, document: SourceDocument) -> None:
        """Create semantic chunks with overlapping windows"""
        content = document.content
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = min(start + self.config.chunk_size, len(content))
            chunk_content = content[start:end]

            # Generate embeddings for semantic search
            embedding = self.embedding_model.encode(chunk_content, show_progress_bar=False).tolist()

            chunk = ContentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document=document,
                content=chunk_content,
                chunk_index=chunk_index,
                embedding=embedding,
                metadata={
                    "document_title": document.title,
                    "document_type": document.doc_type,
                    "source": document.source,
                    "document_id": str(document.id),
                    "chunk_length": len(chunk_content),
                    "start_position": start,
                    "end_position": end
                },
            )
            chunks.append(chunk)
            start = end - self.config.chunk_overlap
            chunk_index += 1

        for chunk in chunks:
            chunk.save()

        self.stats["chunks_created"] += len(chunks)
        logger.info(f"Created {len(chunks)} chunks for document {document.id}")

    def check_duplicate(self, document: SourceDocument) -> bool:
        """Check for duplicate content using semantic similarity"""
        query_embedding = self.embedding_model.encode(document.content, show_progress_bar=False).tolist()

        # Check against existing chunks for similarity
        existing_chunks = ContentChunk.objects().limit(100)  # Sample for performance
        for chunk in existing_chunks:
            if chunk.embedding:
                similarity = cosine_similarity(
                    [query_embedding],
                    [chunk.embedding]
                )[0][0]
                if similarity > 0.95:  # High similarity threshold
                    logger.info(f"Duplicate detected for document {document.id} (similarity: {similarity:.3f})")
                    return True
        return False

    def store_concept(self, concept: str, document_id: str) -> str:
        """Store concept with embedding for semantic relationships"""
        embedding = self.embedding_model.encode(concept, show_progress_bar=False).tolist()
        concept_obj = Concept(
            name=concept,
            document_id=document_id,
            embedding=embedding,
        )
        concept_obj.save()
        self.stats["concepts_extracted"] += 1
        logger.debug(f"Stored concept: {concept} for document {document_id}")
        return concept_obj.id

    def search_relevant_content(self, query: str, n_results: int = 10, min_score: float = 0.3) -> List[Dict]:
        """Advanced semantic search with query expansion and relationship scoring"""
        try:
            # Query expansion using Gemini
            exp_response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Generate 3-5 synonyms, related terms, or alternative phrasings for: '{query}'. Return only the terms, one per line.",
            )
            expanded_text = exp_response.candidates[0].content.parts[0].text.strip()
            expanded_queries = [query] + [line.strip() for line in expanded_text.splitlines()[:4] if line.strip()]
            logger.debug(f"Expanded query: {query} -> {expanded_queries}")
        except Exception as e:
            logger.warning(f"⚠️ Gemini expansion failed, fallback to original query: {e}")
            expanded_queries = [query]

        all_results = []

        # Search with each expanded query
        for exp_query in expanded_queries:
            query_embedding = self.embedding_model.encode(exp_query, show_progress_bar=False).tolist()

            # Get all chunks and calculate similarity manually for better control
            chunks = ContentChunk.objects().limit(200)  # Reasonable limit for performance

            for chunk in chunks:
                if chunk.embedding:
                    similarity = cosine_similarity([query_embedding], [chunk.embedding])[0][0]

                    if similarity >= min_score:
                        # Calculate relationship bonus
                        relationship_bonus = self._calculate_relationship_bonus(chunk.metadata.get('document_id'))

                        result = {
                            'content': chunk.content,
                            'metadata': chunk.metadata,
                            'id': chunk.id,
                            'similarity': similarity,
                            'relationship_bonus': relationship_bonus,
                            'score': similarity + relationship_bonus,
                            'query_used': exp_query
                        }
                        all_results.append(result)

        # Remove duplicates and sort by score
        seen_chunks = set()
        unique_results = []
        for result in all_results:
            if result['id'] not in seen_chunks:
                unique_results.append(result)
                seen_chunks.add(result['id'])

        unique_results.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Found {len(unique_results)} relevant chunks for query: '{query}'")
        return unique_results[:n_results]

    def _calculate_relationship_bonus(self, document_id: str) -> float:
        """Calculate bonus score based on concept relationships"""
        if not document_id:
            return 0.0

        concepts = Concept.objects(document_id=document_id)
        relationship_count = 0

        for concept in concepts:
            relationships = Relationship.objects(concept1_id=concept.id) + Relationship.objects(concept2_id=concept.id)
            relationship_count += len(relationships)

        # Normalize bonus (max 0.2 bonus points)
        return min(relationship_count * 0.02, 0.2)

    def get_memory_stats(self) -> Dict:
        """Get memory system statistics"""
        return {
            **self.stats,
            "total_documents": SourceDocument.objects.count(),
            "total_chunks": ContentChunk.objects.count(),
            "total_concepts": Concept.objects.count(),
            "total_relationships": Relationship.objects.count()
        }

    def build_knowledge_graph(self, document_id: str) -> Dict:
        """Build knowledge graph for a specific document"""
        concepts = Concept.objects(document_id=document_id)
        relationships = []

        for concept in concepts:
            rels = Relationship.objects(concept1_id=concept.id)
            for rel in rels:
                concept2 = Concept.objects(id=rel.concept2_id).first()
                if concept2:
                    relationships.append({
                        'from': concept.name,
                        'to': concept2.name,
                        'type': rel.relation_type
                    })

        return {
            'document_id': document_id,
            'concepts': [c.name for c in concepts],
            'relationships': relationships,
            'graph_size': len(concepts)
        }
        return all_results[:n_results]
