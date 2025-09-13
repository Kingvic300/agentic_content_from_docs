from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mongoengine import (
    Document,
    StringField,
    EmailField,
    DateTimeField,
    ListField,
    DictField,
    FloatField,
    IntField,
    ReferenceField,
)
from werkzeug.security import generate_password_hash, check_password_hash
import utils.utils as utils


class User(Document):
    meta = {"collection": "users"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    username = StringField(required=True, unique=True, max_length=50)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super(User, self).save(*args, **kwargs)


class SourceDocument(Document):
    meta = {"collection": "documents"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    title = StringField(required=True, max_length=200)
    content = StringField(required=True)
    source = StringField(required=True)
    url = StringField()
    doc_type = StringField(required=True, choices=["tutorial", "reference", "example"])
    metadata = DictField()
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "doc_type": self.doc_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ContentChunk(Document):
    meta = {"collection": "content_chunks"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    document = ReferenceField(SourceDocument, required=True, reverse_delete_rule=2)  # CASCADE
    content = StringField(required=True)
    chunk_index = IntField(required=True)
    embedding = ListField(FloatField())
    metadata = DictField()
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": str(self.document.id) if self.document else None,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GeneratedContent(Document):
    meta = {"collection": "generated_content"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    title = StringField(required=True, max_length=200)
    content_type = StringField(required=True, choices=["youtube", "book", "tutorial", "interactive"])
    content = StringField(required=True)
    source_documents = ListField(StringField())  # store document IDs
    metadata = DictField()
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content_type": self.content_type,
            "content": self.content,
            "source_documents": self.source_documents,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Concept(Document):
    meta = {"collection": "concepts"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    name = StringField(required=True, max_length=200)
    document_id = StringField()
    embedding = ListField(FloatField())
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "document_id": self.document_id,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Relationship(Document):
    meta = {"collection": "relationships"}

    id = StringField(primary_key=True, default=utils.generate_uuid)
    concept1_id = StringField(required=True)
    concept2_id = StringField(required=True)
    relation_type = StringField(required=True, default="related_to")
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "concept1_id": self.concept1_id,
            "concept2_id": self.concept2_id,
            "relation_type": self.relation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }