"""Feedback model for user ratings and comments."""

from sqlalchemy import Column, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Feedback(BaseModel):
    """User feedback on knowledge items."""
    
    __tablename__ = "feedback"
    
    # Foreign Keys
    knowledge_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Feedback Information
    is_helpful = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    
    # Relationships
    knowledge_item = relationship("KnowledgeItem", back_populates="feedback")
    user = relationship("User", back_populates="feedback")
    
    def __repr__(self):
        return f"<Feedback(item={self.knowledge_item_id}, helpful={self.is_helpful})>"