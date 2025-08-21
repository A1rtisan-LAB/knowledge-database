"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.search_query import SearchQuery
from app.models.user import User
from app.auth.dependencies import get_current_active_user

router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get analytics overview for the organization.
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Get total items count
    total_items_result = await db.execute(
        select(func.count(KnowledgeItem.id)).where(
            KnowledgeItem.organization_id == current_user.organization_id
        )
    )
    total_items = total_items_result.scalar()
    
    # Get published items count
    published_items_result = await db.execute(
        select(func.count(KnowledgeItem.id)).where(
            and_(
                KnowledgeItem.organization_id == current_user.organization_id,
                KnowledgeItem.status == ContentStatus.PUBLISHED
            )
        )
    )
    published_items = published_items_result.scalar()
    
    # Get total views
    total_views_result = await db.execute(
        select(func.sum(KnowledgeItem.view_count)).where(
            KnowledgeItem.organization_id == current_user.organization_id
        )
    )
    total_views = total_views_result.scalar() or 0
    
    # Get total searches
    total_searches_result = await db.execute(
        select(func.count(SearchQuery.id)).where(
            and_(
                SearchQuery.organization_id == current_user.organization_id,
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            )
        )
    )
    total_searches = total_searches_result.scalar()
    
    return {
        "total_items": total_items,
        "published_items": published_items,
        "total_views": total_views,
        "total_searches": total_searches,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    }


@router.get("/popular")
async def get_popular_content(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    period: str = Query("week", regex="^(day|week|month|year)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get popular content based on views and feedback.
    """
    # Calculate date range
    if period == "day":
        start_date = datetime.utcnow() - timedelta(days=1)
    elif period == "week":
        start_date = datetime.utcnow() - timedelta(weeks=1)
    elif period == "month":
        start_date = datetime.utcnow() - timedelta(days=30)
    else:  # year
        start_date = datetime.utcnow() - timedelta(days=365)
    
    # Query popular items
    query = select(KnowledgeItem).where(
        and_(
            KnowledgeItem.organization_id == current_user.organization_id,
            KnowledgeItem.status == ContentStatus.PUBLISHED,
            KnowledgeItem.published_at >= start_date
        )
    ).order_by(KnowledgeItem.view_count.desc()).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return [
        {
            "id": item.id,
            "title_ko": item.title_ko,
            "title_en": item.title_en,
            "type": item.type,
            "view_count": item.view_count,
            "helpful_count": item.helpful_count,
            "helpful_percentage": item.helpful_percentage
        }
        for item in items
    ]


@router.get("/search-queries")
async def get_search_query_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    period: str = Query("week", regex="^(day|week|month)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get search query analytics.
    """
    # Calculate date range
    if period == "day":
        start_date = datetime.utcnow() - timedelta(days=1)
    elif period == "week":
        start_date = datetime.utcnow() - timedelta(weeks=1)
    else:  # month
        start_date = datetime.utcnow() - timedelta(days=30)
    
    # Get top search queries
    query = select(
        SearchQuery.query_text,
        func.count(SearchQuery.id).label('count'),
        func.avg(SearchQuery.results_count).label('avg_results')
    ).where(
        and_(
            SearchQuery.organization_id == current_user.organization_id,
            SearchQuery.created_at >= start_date
        )
    ).group_by(SearchQuery.query_text).order_by(func.count(SearchQuery.id).desc()).limit(limit)
    
    result = await db.execute(query)
    queries = result.all()
    
    return [
        {
            "query": q.query_text,
            "count": q.count,
            "avg_results": float(q.avg_results) if q.avg_results else 0
        }
        for q in queries
    ]