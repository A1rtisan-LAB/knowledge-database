"""Search query model for analytics and tracking."""

from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.knowledge_item import LanguageCode


class SearchQuery(BaseModel):
    """Search query log for analytics."""
    
    __tablename__ = "search_queries"
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Query Information
    query_text = Column(Text, nullable=False)
    language = Column(String(2), nullable=True)
    filters = Column(JSON, default={}, nullable=False)
    
    # Results Information
    results_count = Column(Integer, default=0, nullable=False)
    clicked_results = Column(JSON, default=[], nullable=False)
    search_duration_ms = Column(Integer, nullable=True)
    
    # Session Tracking
    session_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="search_queries")
    user = relationship("User", back_populates="search_queries")
    
    def __repr__(self):
        return f"<SearchQuery(query={self.query_text[:50]}, results={self.results_count})>"