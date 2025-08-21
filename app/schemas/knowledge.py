"""Knowledge item schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator


class KnowledgeItemBase(BaseModel):
    """Base knowledge item schema."""
    type: str
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    category_id: Optional[UUID] = None
    title_ko: str = Field(..., max_length=500)
    title_en: str = Field(..., max_length=500)
    content_ko: str
    content_en: str
    summary_ko: Optional[str] = None
    summary_en: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    seo_title_ko: Optional[str] = Field(None, max_length=255)
    seo_title_en: Optional[str] = Field(None, max_length=255)
    seo_description_ko: Optional[str] = None
    seo_description_en: Optional[str] = None
    seo_keywords: List[str] = []


class KnowledgeItemCreate(KnowledgeItemBase):
    """Knowledge item creation schema."""
    pass


class KnowledgeItemUpdate(BaseModel):
    """Knowledge item update schema."""
    category_id: Optional[UUID] = None
    title_ko: Optional[str] = Field(None, max_length=500)
    title_en: Optional[str] = Field(None, max_length=500)
    content_ko: Optional[str] = None
    content_en: Optional[str] = None
    summary_ko: Optional[str] = None
    summary_en: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    seo_title_ko: Optional[str] = Field(None, max_length=255)
    seo_title_en: Optional[str] = Field(None, max_length=255)
    seo_description_ko: Optional[str] = None
    seo_description_en: Optional[str] = None
    seo_keywords: Optional[List[str]] = None


class CategoryInfo(BaseModel):
    """Category information schema."""
    id: UUID
    name_ko: str
    name_en: str
    slug: str
    
    class Config:
        from_attributes = True


class KnowledgeItemResponse(BaseModel):
    """Knowledge item response schema."""
    id: UUID
    type: str
    slug: str
    category: Optional[CategoryInfo] = None
    title_ko: str
    title_en: str
    summary_ko: Optional[str]
    summary_en: Optional[str]
    tags: List[str]
    status: str
    version: int
    view_count: int
    helpful_count: int
    not_helpful_count: int
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class KnowledgeItemDetailResponse(KnowledgeItemResponse):
    """Detailed knowledge item response schema."""
    content_ko: str
    content_en: str
    metadata: Dict[str, Any]
    seo_title_ko: Optional[str]
    seo_title_en: Optional[str]
    seo_description_ko: Optional[str]
    seo_description_en: Optional[str]
    seo_keywords: List[str]
    related_items: Optional[List[KnowledgeItemResponse]] = None
    
    class Config:
        from_attributes = True


class KnowledgeItemListResponse(BaseModel):
    """Knowledge item list response schema."""
    items: List[KnowledgeItemResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class KnowledgeVersionResponse(BaseModel):
    """Knowledge version response schema."""
    id: UUID
    version_number: int
    title_ko: Optional[str]
    title_en: Optional[str]
    change_summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True