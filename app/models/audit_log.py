"""Audit log model for tracking system changes."""

from enum import Enum
from sqlalchemy import Column, String, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AuditAction(str, Enum):
    """Audit action enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    ARCHIVE = "archive"
    RESTORE = "restore"
    VIEW = "view"


class AuditLog(BaseModel):
    """Audit log for tracking all system changes."""
    
    __tablename__ = "audit_logs"
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Audit Information
    action = Column(SQLEnum(AuditAction), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Change Details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Request Information
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(action={self.action}, entity={self.entity_type}, user={self.user_id})>"