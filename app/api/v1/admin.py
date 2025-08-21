"""Admin API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.auth.dependencies import require_admin
from app.auth.security import get_password_hash

router = APIRouter()


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    page: int = 1,
    limit: int = 20
):
    """
    List all users in the organization (admin only).
    """
    offset = (page - 1) * limit
    
    query = select(User).where(
        User.organization_id == current_user.organization_id
    ).offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new user (admin only).
    """
    # Check if email already exists
    existing = await db.execute(
        select(User).where(
            User.email == user_data["email"]
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )
    
    # Create user
    user = User(
        organization_id=current_user.organization_id,
        email=user_data["email"],
        username=user_data["username"],
        full_name=user_data.get("full_name"),
        hashed_password=get_password_hash(user_data["password"]),
        role=UserRole(user_data.get("role", UserRole.VIEWER)),
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role
    }


@router.post("/bulk-import", status_code=status.HTTP_202_ACCEPTED)
async def bulk_import_knowledge(
    file: UploadFile = File(...),
    format: str = "json",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Bulk import knowledge items from file (admin only).
    """
    # Validate file format
    if format not in ["csv", "json", "markdown"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Supported formats: csv, json, markdown"
        )
    
    # In production, this would:
    # 1. Upload file to storage
    # 2. Create a background job to process the file
    # 3. Return job ID for tracking
    
    return {
        "job_id": str(UUID("12345678-1234-5678-1234-567812345678")),
        "status": "pending",
        "message": f"Import job created for {file.filename}"
    }


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED)
async def trigger_reindex(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Trigger search index rebuild (admin only).
    """
    # In production, this would:
    # 1. Create a background job to reindex all content
    # 2. Return job ID for tracking
    
    return {
        "status": "started",
        "message": "Reindexing job has been queued",
        "force": force
    }