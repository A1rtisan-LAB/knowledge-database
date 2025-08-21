"""Organization model for multi-tenancy support."""

import uuid
from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Organization(BaseModel):
    """Organization model for multi-tenant support."""
    
    __tablename__ = "organizations"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    settings = Column(JSON, default={}, nullable=False)
    api_key = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="organization", cascade="all, delete-orphan")
    knowledge_items = relationship("KnowledgeItem", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
    search_queries = relationship("SearchQuery", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization(slug={self.slug}, name={self.name})>"