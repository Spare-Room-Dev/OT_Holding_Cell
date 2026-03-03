"""Prisoner query routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.prisoners import PrisonerDetailResponse, PrisonerListResponse
from app.services.prisoner_query_service import (
    InvalidCursorTokenError,
    get_prisoner_detail,
    list_prisoners,
)

router = APIRouter()


@router.get("/prisoners", response_model=PrisonerListResponse)
def get_prisoners(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    session: Session = Depends(get_db_session),
) -> PrisonerListResponse:
    try:
        return list_prisoners(
            session=session,
            limit=limit,
            cursor=cursor,
            country=country,
        )
    except InvalidCursorTokenError as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor token") from exc


@router.get("/prisoners/{prisoner_id}", response_model=PrisonerDetailResponse)
def get_prisoner_by_id(
    prisoner_id: int,
    session: Session = Depends(get_db_session),
) -> PrisonerDetailResponse:
    detail = get_prisoner_detail(session=session, prisoner_id=prisoner_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Prisoner not found")
    return detail
