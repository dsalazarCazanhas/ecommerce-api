"""CRUD helpers for server-side idempotency records."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.models.auth import IdempotencyRecord, IdempotencyStatus


def get_by_user_and_key(
    session: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    scope: str,
) -> IdempotencyRecord | None:
    return session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.scope == scope,
        )
    ).first()


def create_processing(
    session: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    scope: str,
) -> IdempotencyRecord:
    record = IdempotencyRecord(
        user_id=user_id,
        scope=scope,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status=IdempotencyStatus.PROCESSING,
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = get_by_user_and_key(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
            scope=scope,
        )
        if existing is None:
            raise
        return existing

    session.refresh(record)
    return record


def mark_completed(
    session: Session,
    *,
    record: IdempotencyRecord,
    response_status_code: int,
    response_body: str,
) -> IdempotencyRecord:
    record.status = IdempotencyStatus.COMPLETED
    record.response_status_code = response_status_code
    record.response_body = response_body
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def mark_failed(
    session: Session,
    *,
    record: IdempotencyRecord,
    response_status_code: int,
    response_body: str,
) -> IdempotencyRecord:
    record.status = IdempotencyStatus.FAILED
    record.response_status_code = response_status_code
    record.response_body = response_body
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def prune_stale_records(
    session: Session,
    *,
    ttl_hours: int,
) -> int:
    """Delete stale idempotency records older than TTL to keep table bounded."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    stale_records = session.exec(
        select(IdempotencyRecord).where(IdempotencyRecord.updated_at < cutoff)
    ).all()

    deleted_count = 0
    for record in stale_records:
        session.delete(record)
        deleted_count += 1

    if deleted_count:
        session.commit()

    return deleted_count
