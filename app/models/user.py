"""User model with role-based access control."""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class UserRole(str, Enum):
    """User role enumeration."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class User(BaseModel):
    """User model with RBAC support."""
    
    __tablename__ = "users"
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # User Information
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Role and Permissions
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    preferences = Column(JSON, default={}, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    created_items = relationship("KnowledgeItem", foreign_keys="KnowledgeItem.created_by", back_populates="creator")
    updated_items = relationship("KnowledgeItem", foreign_keys="KnowledgeItem.updated_by", back_populates="updater")
    versions = relationship("KnowledgeVersion", back_populates="created_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    search_queries = relationship("SearchQuery", back_populates="user")
    
    def __repr__(self):
        return f"<User(email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    @property
    def can_edit(self) -> bool:
        """Check if user can edit content."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EDITOR]
    
    @property
    def can_review(self) -> bool:
        """Check if user can review content."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EDITOR, UserRole.REVIEWER]