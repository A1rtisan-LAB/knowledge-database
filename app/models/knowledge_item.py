"""Knowledge item models including versions and embeddings."""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel


class ContentType(str, Enum):
    """Content type enumeration."""
    ARTICLE = "article"
    FAQ = "faq"
    GUIDE = "guide"
    API_DOC = "api_doc"
    GLOSSARY = "glossary"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"


class ContentStatus(str, Enum):
    """Content status enumeration."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class LanguageCode(str, Enum):
    """Language code enumeration."""
    KO = "ko"
    EN = "en"


class KnowledgeItem(BaseModel):
    """Main knowledge content model."""
    
    __tablename__ = "knowledge_items"
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Content Information
    type = Column(SQLEnum(ContentType), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    
    # Bilingual Content
    title_ko = Column(String(500), nullable=False)
    title_en = Column(String(500), nullable=False)
    content_ko = Column(Text, nullable=False)
    content_en = Column(Text, nullable=False)
    summary_ko = Column(Text, nullable=True)
    summary_en = Column(Text, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=[], nullable=False)
    content_metadata = Column("metadata", JSON, default={}, nullable=False)
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    # SEO Fields
    seo_title_ko = Column(String(255), nullable=True)
    seo_title_en = Column(String(255), nullable=True)
    seo_description_ko = Column(Text, nullable=True)
    seo_description_en = Column(Text, nullable=True)
    seo_keywords = Column(JSON, default=[], nullable=False)
    
    # Statistics
    view_count = Column(Integer, default=0, nullable=False)
    helpful_count = Column(Integer, default=0, nullable=False)
    not_helpful_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="knowledge_items")
    category = relationship("Category", back_populates="knowledge_items")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_items")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_items")
    versions = relationship("KnowledgeVersion", back_populates="knowledge_item", cascade="all, delete-orphan")
    embeddings = relationship("KnowledgeEmbedding", back_populates="knowledge_item", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="knowledge_item", cascade="all, delete-orphan")
    
    # Related items (self-referential many-to-many)
    related_items = relationship(
        "KnowledgeItem",
        secondary="related_items",
        primaryjoin="KnowledgeItem.id==RelatedItem.source_item_id",
        secondaryjoin="KnowledgeItem.id==RelatedItem.target_item_id",
        viewonly=True
    )
    
    def __repr__(self):
        return f"<KnowledgeItem(slug={self.slug}, type={self.type}, status={self.status})>"
    
    @property
    def is_published(self) -> bool:
        """Check if item is published."""
        return self.status == ContentStatus.PUBLISHED
    
    @property
    def helpful_percentage(self) -> float:
        """Calculate helpful percentage."""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0.0
        return (self.helpful_count / total) * 100


class KnowledgeVersion(BaseModel):
    """Version history for knowledge items."""
    
    __tablename__ = "knowledge_versions"
    
    # Foreign Keys
    knowledge_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Version Information
    version_number = Column(Integer, nullable=False)
    
    # Content Snapshot
    title_ko = Column(String(500), nullable=True)
    title_en = Column(String(500), nullable=True)
    content_ko = Column(Text, nullable=True)
    content_en = Column(Text, nullable=True)
    summary_ko = Column(Text, nullable=True)
    summary_en = Column(Text, nullable=True)
    change_summary = Column(Text, nullable=True)
    
    # Relationships
    knowledge_item = relationship("KnowledgeItem", back_populates="versions")
    created_by_user = relationship("User", back_populates="versions")
    
    def __repr__(self):
        return f"<KnowledgeVersion(item_id={self.knowledge_item_id}, version={self.version_number})>"


class KnowledgeEmbedding(BaseModel):
    """Vector embeddings for semantic search."""
    
    __tablename__ = "knowledge_embeddings"
    
    # Foreign Keys
    knowledge_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    
    # Embedding Information
    language = Column(SQLEnum(LanguageCode), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    content_metadata = Column("metadata", JSON, default={}, nullable=False)
    
    # Relationships
    knowledge_item = relationship("KnowledgeItem", back_populates="embeddings")
    
    def __repr__(self):
        return f"<KnowledgeEmbedding(item_id={self.knowledge_item_id}, language={self.language}, chunk={self.chunk_index})>"


class RelatedItem(BaseModel):
    """Many-to-many relationship for related knowledge items."""
    
    __tablename__ = "related_items"
    
    # Foreign Keys
    source_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    target_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    
    # Relationship Information
    relevance_score = Column(Float, default=0.5, nullable=False)
    is_manual = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<RelatedItem(source={self.source_item_id}, target={self.target_item_id}, score={self.relevance_score})>"