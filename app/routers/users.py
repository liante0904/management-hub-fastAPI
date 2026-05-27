"""
Users Router — 텔레그램 유저 관리 API

- 유저 목록 조회 (페이지네이션)
- 유저 상세 조회
- admin 권한 부여/회수
- 유저 상태 변경 (active / blocked / inactive)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from .admin import get_current_admin

load_dotenv()

logger = logging.getLogger("management-hub.users")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None
    is_admin: bool = False
    created_at: Optional[int] = None

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    users: list[UserOut]
    total: int
    page: int
    page_size: int


class UserStatusUpdate(BaseModel):
    status: str = Field(..., description="active | blocked | inactive")


class AdminToggle(BaseModel):
    is_admin: bool


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="active | blocked | inactive"),
    search: Optional[str] = Query(None, description="이름 또는 username 검색"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """유저 목록 조회 (admin 전용)"""
    where = []
    params: dict = {}

    if status:
        where.append("status = :status")
        params["status"] = status
    if search:
        where.append("(first_name ILIKE :search OR last_name ILIKE :search OR username ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(text(f"SELECT COUNT(*) FROM tbl_sec_reports_telegram_users {where_clause}"), params).scalar() or 0
    offset = (page - 1) * page_size
    rows = db.execute(
        text(
            f"SELECT id, first_name, last_name, username, photo_url, status, is_admin, created_at "
            f"FROM tbl_sec_reports_telegram_users {where_clause} "
            f"ORDER BY id ASC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    users = [
        UserOut(
            id=r[0], first_name=r[1], last_name=r[2], username=r[3],
            photo_url=r[4], status=r[5], is_admin=r[6] or False, created_at=r[7],
        )
        for r in rows
    ]
    return UserListOut(users=users, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """유저 상세 조회"""
    row = db.execute(
        text(
            "SELECT id, first_name, last_name, username, photo_url, status, is_admin, created_at "
            "FROM tbl_sec_reports_telegram_users WHERE id = :uid"
        ),
        {"uid": user_id},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(
        id=row[0], first_name=row[1], last_name=row[2], username=row[3],
        photo_url=row[4], status=row[5], is_admin=row[6] or False, created_at=row[7],
    )


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """유저 상태 변경 (active / blocked / inactive)"""
    valid_statuses = {"active", "blocked", "inactive"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    result = db.execute(
        text("UPDATE tbl_sec_reports_telegram_users SET status = :status WHERE id = :uid"),
        {"status": body.status, "uid": user_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "status": body.status, "updated": True}


@router.put("/{user_id}/admin")
async def toggle_admin(
    user_id: int,
    body: AdminToggle,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """admin 권한 부여/회수"""
    result = db.execute(
        text("UPDATE tbl_sec_reports_telegram_users SET is_admin = :is_admin WHERE id = :uid"),
        {"is_admin": body.is_admin, "uid": user_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "is_admin": body.is_admin, "updated": True}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """유저 삭제 (관리자 전용)"""
    result = db.execute(
        text("DELETE FROM tbl_sec_reports_telegram_users WHERE id = :uid"),
        {"uid": user_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "deleted": True}
