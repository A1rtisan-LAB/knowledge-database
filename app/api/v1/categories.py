"""Categories API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.category import Category
from app.models.user import User
from app.auth.dependencies import get_current_active_user, require_editor

router = APIRouter()


@router.get("")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    parent_id: Optional[UUID] = None,
    language: str = Query("en", regex="^(en|ko)$")
):
    """
    List categories with optional parent filter.
    """
    query = select(Category).where(
        and_(
            Category.organization_id == current_user.organization_id,
            Category.is_active == True
        )
    )
    
    if parent_id:
        query = query.where(Category.parent_id == parent_id)
    else:
        query = query.where(Category.parent_id.is_(None))
    
    query = query.order_by(Category.display_order, Category.name_en)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return [
        {
            "id": cat.id,
            "parent_id": cat.parent_id,
            "name": cat.name_en if language == "en" else cat.name_ko,
            "slug": cat.slug,
            "description": cat.description_en if language == "en" else cat.description_ko,
            "icon": cat.icon,
            "display_order": cat.display_order,
            "item_count": cat.item_count
        }
        for cat in categories
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Create a new category.
    """
    # Check if slug already exists
    existing = await db.execute(
        select(Category).where(
            and_(
                Category.organization_id == current_user.organization_id,
                Category.slug == category_data["slug"]
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this slug already exists"
        )
    
    category = Category(
        **category_data,
        organization_id=current_user.organization_id
    )
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return {
        "id": category.id,
        "name_ko": category.name_ko,
        "name_en": category.name_en,
        "slug": category.slug,
        "parent_id": category.parent_id
    }


@router.get("/{id}")
async def get_category(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    language: str = Query("en", regex="^(en|ko)$")
):
    """
    Get category details with children.
    """
    query = select(Category).where(
        and_(
            Category.id == id,
            Category.organization_id == current_user.organization_id
        )
    ).options(selectinload(Category.children))
    
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "id": category.id,
        "parent_id": category.parent_id,
        "name": category.name_en if language == "en" else category.name_ko,
        "slug": category.slug,
        "description": category.description_en if language == "en" else category.description_ko,
        "icon": category.icon,
        "display_order": category.display_order,
        "item_count": category.item_count,
        "children": [
            {
                "id": child.id,
                "name": child.name_en if language == "en" else child.name_ko,
                "slug": child.slug,
                "item_count": child.item_count
            }
            for child in category.children
        ]
    }