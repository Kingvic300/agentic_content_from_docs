from typing import Dict, List, Optional
from sentence_transformers import SentenceTransformer
import google.genai as genai

from models.models import SourceDocument, ContentChunk, Concept, Relationship
from configuration.configuration import Configuration as Config, logger


def store_relationship(concept1: str, concept2: str, relation_type: str):
    c1 = Concept.objects(name=concept1).first()
    c2 = Concept.objects(name=concept2).first()
    if c1 and c2:
        rel = Relationship(
            concept1_id=c1.id,
            concept2_id=c2.id,
            relation_type=relation_type,
        )
        rel.save()


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

    def store_document(self, document: SourceDocument) -> None:
        try:
            if not self.check_duplicate(document):
                document.save()
                self._create_and_store_chunks(document)
        except Exception as e:
            logger.error(f"Error storing document {document.id}: {e}")

    def _create_and_store_chunks(self, document: SourceDocument) -> None:
        content = document.content
        chunks = []
        start = 0
        chunk_index = 0
        while start < len(content):
            end = min(start + self.config.chunk_size, len(content))
            chunk_content = content[start:end]
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
                },
            )
            chunks.append(chunk)
            start = end - self.config.chunk_overlap
            chunk_index += 1

        for chunk in chunks:
            chunk.save()

    def check_duplicate(self, document: SourceDocument) -> bool:
        query_embedding = self.embedding_model.encode(document.content, show_progress_bar=False).tolist()
        existing = ContentChunk.objects(embedding__near=query_embedding, embedding__distance__lt=0.1)
        if existing:
            logger.info(f"Duplicate detected for document {document.id}")
            return True
        return False

    def store_concept(self, concept: str, document_id: str):
        embedding = self.embedding_model.encode(concept, show_progress_bar=False).tolist()
        concept_obj = Concept(
            name=concept,
            document_id=document_id,
            embedding=embedding,
        )
        concept_obj.save()

    def search_relevant_content(self, query: str, n_results: int = 10) -> List[Dict]:
        try:
            exp_response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Generate 3 synonyms or related terms for query: {query}",
            )
            expanded_text = exp_response.candidates[0].content.parts[0].text
            expanded_queries = [query] + expanded_text.splitlines()[:3]
        except Exception as e:
            logger.warning(f"⚠️ Gemini expansion failed, fallback to original query: {e}")
            expanded_queries = [query]

        all_results = []
        for exp_query in expanded_queries:
            query_embedding = self.embedding_model.encode(exp_query, show_progress_bar=False).tolist()
            chunks = ContentChunk.objects(embedding__near=query_embedding).limit(
                max(1, n_results // len(expanded_queries))
            )
            for chunk in chunks:
                all_results.append({
                    'content': chunk.content,
                    'metadata': chunk.metadata,
                    'id': chunk.id,
                    'distance': 0.0,
                })

        for res in all_results:
            score = 1.0
            concepts = Concept.objects(document_id=res['metadata'].get('document_id'))
            for concept in concepts:
                if Relationship.objects(concept1_id=concept.id) or Relationship.objects(concept2_id=concept.id):
                    score += 0.1
            res['score'] = score

        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[:n_results]
