"""Knowledge items API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.knowledge_item import KnowledgeItem, KnowledgeVersion, ContentStatus, ContentType
from app.models.user import User
from app.auth.dependencies import get_current_active_user, get_optional_current_user, require_editor
from app.schemas.knowledge import (
    KnowledgeItemCreate,
    KnowledgeItemUpdate,
    KnowledgeItemResponse,
    KnowledgeItemDetailResponse,
    KnowledgeItemListResponse,
    KnowledgeVersionResponse
)
from app.services.search import index_knowledge_item, delete_from_index
from app.services.embeddings import generate_embeddings

router = APIRouter()


@router.get("", response_model=KnowledgeItemListResponse)
async def list_knowledge_items(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[UUID] = None,
    type: Optional[ContentType] = None,
    status: Optional[ContentStatus] = None,
    tags: Optional[List[str]] = Query(None),
    language: str = Query("en", regex="^(en|ko)$"),
    sort: str = Query("updated_at", regex="^(created_at|updated_at|title|views|helpful)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
) -> KnowledgeItemListResponse:
    """
    List knowledge items with filtering and pagination.
    """
    # Build query
    query = select(KnowledgeItem)
    
    # Apply filters
    filters = []
    
    if category_id:
        filters.append(KnowledgeItem.category_id == category_id)
    
    if type:
        filters.append(KnowledgeItem.type == type)
    
    if status:
        filters.append(KnowledgeItem.status == status)
    elif not current_user or not current_user.can_edit:
        # Non-editors can only see published items
        filters.append(KnowledgeItem.status == ContentStatus.PUBLISHED)
    
    if current_user:
        filters.append(KnowledgeItem.organization_id == current_user.organization_id)
    
    if tags:
        # Filter by tags (items must have all specified tags)
        for tag in tags:
            filters.append(KnowledgeItem.tags.contains([tag]))
    
    if filters:
        query = query.where(and_(*filters))
    
    # Apply sorting
    sort_column = {
        "created_at": KnowledgeItem.created_at,
        "updated_at": KnowledgeItem.updated_at,
        "title": KnowledgeItem.title_en if language == "en" else KnowledgeItem.title_ko,
        "views": KnowledgeItem.view_count,
        "helpful": KnowledgeItem.helpful_count
    }.get(sort, KnowledgeItem.updated_at)
    
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Get total count
    count_query = select(func.count()).select_from(KnowledgeItem)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Include relationships
    query = query.options(selectinload(KnowledgeItem.category))
    
    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()
    
    return KnowledgeItemListResponse(
        items=[KnowledgeItemResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        has_more=(offset + limit) < total
    )


@router.get("/{id}", response_model=KnowledgeItemDetailResponse)
async def get_knowledge_item(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    language: str = Query("en", regex="^(en|ko)$"),
    include_related: bool = Query(False)
) -> KnowledgeItemDetailResponse:
    """
    Get knowledge item by ID.
    """
    # Get item with relationships
    query = select(KnowledgeItem).where(KnowledgeItem.id == id)
    query = query.options(
        selectinload(KnowledgeItem.category),
        selectinload(KnowledgeItem.creator),
        selectinload(KnowledgeItem.updater)
    )
    
    if include_related:
        query = query.options(selectinload(KnowledgeItem.related_items))
    
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check permissions
    if item.status != ContentStatus.PUBLISHED:
        if not current_user or not current_user.can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this item"
            )
    
    # Increment view count
    item.view_count += 1
    await db.commit()
    
    return KnowledgeItemDetailResponse.from_orm(item)


@router.post("", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_item(
    item_data: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor)
) -> KnowledgeItemResponse:
    """
    Create a new knowledge item.
    """
    # Check if slug already exists
    existing = await db.execute(
        select(KnowledgeItem).where(
            and_(
                KnowledgeItem.organization_id == current_user.organization_id,
                KnowledgeItem.slug == item_data.slug
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A knowledge item with this slug already exists"
        )
    
    # Create item
    item = KnowledgeItem(
        **item_data.dict(),
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        updated_by=current_user.id
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    # Generate embeddings and index in OpenSearch (async task)
    await generate_embeddings(item)
    await index_knowledge_item(item)
    
    return KnowledgeItemResponse.from_orm(item)


@router.put("/{id}", response_model=KnowledgeItemResponse)
async def update_knowledge_item(
    id: UUID = Path(...),
    item_data: KnowledgeItemUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor)
) -> KnowledgeItemResponse:
    """
    Update a knowledge item.
    """
    # Get existing item
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check organization
    if item.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this item"
        )
    
    # Update fields
    update_data = item_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_by = current_user.id
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    # Re-index in OpenSearch
    await generate_embeddings(item)
    await index_knowledge_item(item)
    
    return KnowledgeItemResponse.from_orm(item)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_item(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Delete a knowledge item.
    """
    # Get existing item
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check organization
    if item.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this item"
        )
    
    # Soft delete by changing status
    item.status = ContentStatus.DELETED
    item.updated_by = current_user.id
    await db.commit()
    
    # Remove from search index
    await delete_from_index(str(item.id))
    
    return None


@router.post("/{id}/publish", response_model=KnowledgeItemResponse)
async def publish_knowledge_item(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor)
) -> KnowledgeItemResponse:
    """
    Publish a knowledge item.
    """
    # Get existing item
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check organization
    if item.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to publish this item"
        )
    
    # Update status
    item.status = ContentStatus.PUBLISHED
    item.published_at = datetime.utcnow()
    item.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(item)
    
    # Index in OpenSearch
    await index_knowledge_item(item)
    
    return KnowledgeItemResponse.from_orm(item)


@router.get("/{id}/versions", response_model=List[KnowledgeVersionResponse])
async def get_knowledge_versions(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[KnowledgeVersionResponse]:
    """
    Get version history for a knowledge item.
    """
    # Get versions
    result = await db.execute(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.knowledge_item_id == id)
        .order_by(KnowledgeVersion.version_number.desc())
        .options(selectinload(KnowledgeVersion.created_by_user))
    )
    versions = result.scalars().all()
    
    return [KnowledgeVersionResponse.from_orm(v) for v in versions]