"""
Reports Router — 수집된 레포트 관리 API

- tbl_sec_reports: 레포트 목록/검색/필터/상세 (페이지네이션)
- tbl_sec_reports_pdf_archive: PDF 아카이브 상태
- tbl_fnguide_report_summaries: FnGuide 요약 목록
- tbl_report_send_history: 발송 이력
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

logger = logging.getLogger("management-hub.reports")


# ---------------------------------------------------------------------------
# Schemas — Report
# ---------------------------------------------------------------------------

class ReportOut(BaseModel):
    report_id: int
    firm_nm: Optional[str] = None
    article_title: Optional[str] = None
    article_url: Optional[str] = None
    writer: Optional[str] = None
    save_time: Optional[str] = None
    reg_dt: Optional[str] = None
    mkt_tp: Optional[str] = None
    download_status_yn: Optional[str] = None
    sync_status: Optional[int] = 0
    pdf_sync_status: Optional[int] = 0
    gemini_summary: Optional[str] = None
    summary_time: Optional[str] = None
    summary_model: Optional[str] = None


class ReportListOut(BaseModel):
    reports: list[ReportOut]
    total: int
    page: int
    page_size: int


class ReportSyncUpdate(BaseModel):
    sync_status: Optional[int] = Field(None, description="0=대기, 1=처리중, 2=완료, -1=실패")
    pdf_sync_status: Optional[int] = Field(None, description="PDF 동기화 상태")


# ---------------------------------------------------------------------------
# Schemas — PDF Archive
# ---------------------------------------------------------------------------

class PdfArchiveOut(BaseModel):
    report_id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    archive_status: Optional[str] = None
    storage_backend: Optional[str] = None
    has_text: Optional[bool] = None
    is_encrypted: Optional[bool] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Schemas — FnGuide Summary
# ---------------------------------------------------------------------------

class FnGuideSummaryOut(BaseModel):
    summary_id: int
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    report_title: Optional[str] = None
    report_date: Optional[str] = None
    opinion: Optional[str] = None
    target_price: Optional[str] = None
    provider: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None


class FnGuideSummaryListOut(BaseModel):
    summaries: list[FnGuideSummaryOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Schemas — Send History
# ---------------------------------------------------------------------------

class SendHistoryOut(BaseModel):
    id: int
    report_id: int
    user_id: int
    keyword: Optional[str] = None
    sent_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ── tbl_sec_reports ────────────────────────────────────────────────────────

@router.get("", response_model=ReportListOut)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    firm_nm: Optional[str] = Query(None, description="증권사명 검색"),
    reg_dt: Optional[str] = Query(None, description="등록일자 (YYYYMMDD)"),
    sync_status: Optional[int] = Query(None, description="0=대기, 1=처리중, 2=완료, -1=실패"),
    search: Optional[str] = Query(None, description="제목 검색"),
    sort: Optional[str] = Query("save_time DESC", description="정렬 (save_time DESC | reg_dt DESC)"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 목록 조회 (페이지네이션 + 필터)"""
    where = []
    params: dict = {}

    if firm_nm:
        where.append("firm_nm ILIKE :firm_nm")
        params["firm_nm"] = f"%{firm_nm}%"
    if reg_dt:
        where.append("reg_dt = :reg_dt")
        params["reg_dt"] = reg_dt
    if sync_status is not None:
        where.append("sync_status = :sync_status")
        params["sync_status"] = sync_status
    if search:
        where.append("article_title ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    # sort whitelist
    allowed_sorts = {"save_time DESC", "save_time ASC", "reg_dt DESC", "reg_dt ASC", "report_id DESC", "report_id ASC"}
    sort_col = sort if sort in allowed_sorts else "save_time DESC"

    total_row = db.execute(text(f"SELECT COUNT(*) FROM tbl_sec_reports {where_clause}"), params).scalar()
    total = total_row or 0

    offset = (page - 1) * page_size
    rows = db.execute(
        text(
            f"SELECT report_id, firm_nm, article_title, article_url, writer, save_time, reg_dt, mkt_tp, "
            f"download_status_yn, sync_status, pdf_sync_status, gemini_summary, summary_time, summary_model "
            f"FROM tbl_sec_reports {where_clause} "
            f"ORDER BY {sort_col} LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    reports = [
        ReportOut(
            report_id=r[0], firm_nm=r[1], article_title=r[2], article_url=r[3], writer=r[4],
            save_time=r[5], reg_dt=r[6], mkt_tp=r[7], download_status_yn=r[8],
            sync_status=r[9] or 0, pdf_sync_status=r[10] or 0,
            gemini_summary=r[11], summary_time=r[12], summary_model=r[13],
        )
        for r in rows
    ]
    return ReportListOut(reports=reports, total=total, page=page, page_size=page_size)


# ── tbl_fnguide_report_summaries (必 /{report_id} 보다 앞에 위치) ──────────

@router.get("/fnguide", response_model=FnGuideSummaryListOut)
async def list_fnguide_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_name: Optional[str] = Query(None),
    report_date: Optional[str] = Query(None, description="YYYYMMDD"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """FnGuide 요약 목록"""
    where = []
    params: dict = {}
    if company_name:
        where.append("company_name ILIKE :company_name")
        params["company_name"] = f"%{company_name}%"
    if report_date:
        where.append("report_date = :report_date")
        params["report_date"] = report_date

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(text(f"SELECT COUNT(*) FROM tbl_fnguide_report_summaries {where_clause}"), params).scalar() or 0
    offset = (page - 1) * page_size

    rows = db.execute(
        text(
            f"SELECT summary_id, company_name, company_code, report_title, report_date, "
            f"opinion, target_price, provider, author, "
            f"to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at "
            f"FROM tbl_fnguide_report_summaries {where_clause} "
            f"ORDER BY summary_id DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()

    summaries = [
        FnGuideSummaryOut(
            summary_id=r[0], company_name=r[1], company_code=r[2], report_title=r[3],
            report_date=r[4], opinion=r[5], target_price=r[6], provider=r[7], author=r[8],
            created_at=r[9],
        )
        for r in rows
    ]
    return FnGuideSummaryListOut(summaries=summaries, total=total, page=page, page_size=page_size)


# ── tbl_report_send_history (必 /{report_id} 보다 앞에 위치) ───────────────

@router.get("/send-history", response_model=list[SendHistoryOut])
async def list_send_history(
    report_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 발송 이력"""
    where = []
    params: dict = {"limit": limit}
    if report_id:
        where.append("report_id = :report_id")
        params["report_id"] = report_id
    if user_id:
        where.append("user_id = :user_id")
        params["user_id"] = user_id

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(
        text(
            f"SELECT id, report_id, user_id, keyword, "
            f"to_char(sent_at, 'YYYY-MM-DD HH24:MI:SS') as sent_at "
            f"FROM tbl_report_send_history {where_clause} "
            f"ORDER BY id DESC LIMIT :limit"
        ),
        params,
    ).fetchall()

    return [SendHistoryOut(id=r[0], report_id=r[1], user_id=r[2], keyword=r[3], sent_at=r[4]) for r in rows]


# ── /{report_id} 이하 (파라미터 라우트 — 정적 경로 뒤에 위치) ──────────────


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 상세 조회"""
    row = db.execute(
        text(
            "SELECT report_id, firm_nm, article_title, article_url, writer, save_time, reg_dt, mkt_tp, "
            "download_status_yn, sync_status, pdf_sync_status, gemini_summary, summary_time, summary_model "
            "FROM tbl_sec_reports WHERE report_id = :rid"
        ),
        {"rid": report_id},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportOut(
        report_id=row[0], firm_nm=row[1], article_title=row[2], article_url=row[3], writer=row[4],
        save_time=row[5], reg_dt=row[6], mkt_tp=row[7], download_status_yn=row[8],
        sync_status=row[9] or 0, pdf_sync_status=row[10] or 0,
        gemini_summary=row[11], summary_time=row[12], summary_model=row[13],
    )


@router.put("/{report_id}/sync")
async def update_report_sync(
    report_id: int,
    body: ReportSyncUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 동기화 상태 재설정 (재처리 트리거용)"""
    updates = []
    params = {"rid": report_id}
    if body.sync_status is not None:
        updates.append("sync_status = :sync_status")
        params["sync_status"] = body.sync_status
    if body.pdf_sync_status is not None:
        updates.append("pdf_sync_status = :pdf_sync_status")
        params["pdf_sync_status"] = body.pdf_sync_status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.execute(
        text(f"UPDATE tbl_sec_reports SET {', '.join(updates)} WHERE report_id = :rid"),
        params,
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report_id, "updated": True}


# ── tbl_sec_reports_pdf_archive ────────────────────────────────────────────

@router.get("/{report_id}/pdf", response_model=Optional[PdfArchiveOut])
async def get_report_pdf_archive(
    report_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """레포트 PDF 아카이브 상태"""
    row = db.execute(
        text(
            "SELECT report_id, file_path, file_size, page_count, archive_status, storage_backend, "
            "has_text, is_encrypted, "
            "to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at "
            "FROM tbl_sec_reports_pdf_archive WHERE report_id = :rid"
        ),
        {"rid": report_id},
    ).first()
    if not row:
        return None
    return PdfArchiveOut(
        report_id=row[0], file_path=row[1], file_size=row[2], page_count=row[3],
        archive_status=row[4], storage_backend=row[5], has_text=row[6], is_encrypted=row[7],
        created_at=row[8],
    )
