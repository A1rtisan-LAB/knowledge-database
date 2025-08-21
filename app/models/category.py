"""Category model for hierarchical content organization."""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Category(BaseModel):
    """Category model with hierarchical structure."""
    
    __tablename__ = "categories"
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    
    # Category Information
    name_ko = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description_ko = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    icon = Column(String(100), nullable=True)
    
    # Display
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="categories")
    parent = relationship("Category", remote_side="Category.id", backref="children")
    knowledge_items = relationship("KnowledgeItem", back_populates="category")
    
    def __repr__(self):
        return f"<Category(slug={self.slug}, name_en={self.name_en})>"
    
    @property
    def full_path(self) -> str:
        """Get full category path from root to current."""
        if self.parent:
            return f"{self.parent.full_path}/{self.slug}"
        return self.slug
    
    @property
    def item_count(self) -> int:
        """Get count of knowledge items in this category."""
        return len(self.knowledge_items)