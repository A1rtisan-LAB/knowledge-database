"""API router module."""

from fastapi import APIRouter

from app.api.v1 import auth, knowledge, categories, search, analytics, admin

router = APIRouter()

# Include all routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Items"])
router.include_router(categories.router, prefix="/categories", tags=["Categories"])
router.include_router(search.router, prefix="/search", tags=["Search"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])

__all__ = ["router"]