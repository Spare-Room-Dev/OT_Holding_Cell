"""Ingest endpoint routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ingest import IngestPayload
from app.security.forwarder_auth import require_trusted_forwarder, resolve_client_ip
from app.services.ingest_service import process_ingest_payload

router = APIRouter()


@router.post("/ingest", dependencies=[Depends(require_trusted_forwarder)])
async def ingest_payload(
    payload: IngestPayload,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    return process_ingest_payload(
        payload=payload,
        source_ip=resolve_client_ip(request),
        session=session,
    )
