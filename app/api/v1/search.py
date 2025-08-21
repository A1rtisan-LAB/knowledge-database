"""Search API endpoints."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_optional_current_user
from app.services.opensearch import search_knowledge, get_search_suggestions
from app.services.embeddings import find_similar_items

router = APIRouter()


@router.post("/")
async def search(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    language: str = Query("en", regex="^(en|ko)$"),
    search_type: str = Query("hybrid", regex="^(keyword|semantic|hybrid)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_ids: Optional[List[str]] = Query(None),
    types: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None)
):
    """
    Search knowledge base with various filters and search types.
    """
    filters = {}
    if category_ids:
        filters['category_ids'] = category_ids
    if types:
        filters['types'] = types
    if tags:
        filters['tags'] = tags
    
    organization_id = str(current_user.organization_id) if current_user else None
    
    results = await search_knowledge(
        query=query,
        language=language,
        organization_id=organization_id,
        filters=filters,
        page=page,
        limit=limit,
        search_type=search_type
    )
    
    return results


@router.get("/suggest")
async def get_suggestions(
    q: str = Query(..., min_length=2),
    current_user: Optional[User] = Depends(get_optional_current_user),
    language: str = Query("en", regex="^(en|ko)$"),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get search suggestions based on partial query.
    """
    organization_id = str(current_user.organization_id) if current_user else None
    
    suggestions = await get_search_suggestions(
        query=q,
        language=language,
        organization_id=organization_id,
        limit=limit
    )
    
    return suggestions


@router.post("/similar")
async def find_similar(
    text: str,
    language: str = Query("en", regex="^(en|ko)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Find similar content based on semantic similarity.
    """
    similar_items = await find_similar_items(
        text=text,
        language=language,
        limit=limit
    )
    
    return {
        "text": text,
        "language": language,
        "similar_items": [
            {"id": item_id, "similarity": score}
            for item_id, score in similar_items
        ]
    }