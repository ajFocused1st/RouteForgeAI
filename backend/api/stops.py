from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.database.session import get_db_session
from backend.models.stop import Stop
from backend.schemas.stop import StopCreate, StopRead, StopUpdate

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("")
def list_stops(db: Session = Depends(get_db_session)) -> dict:
    stops = db.scalars(select(Stop).order_by(Stop.id)).all()
    return success_response([StopRead.model_validate(stop) for stop in stops])


@router.get("/{stop_id}")
def get_stop(stop_id: int, db: Session = Depends(get_db_session)) -> dict:
    stop = db.get(Stop, stop_id)
    if stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found.",
        )

    return success_response(StopRead.model_validate(stop))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_stop(
    stop_in: StopCreate,
    db: Session = Depends(get_db_session),
) -> dict:
    stop = Stop(**stop_in.model_dump())
    db.add(stop)
    db.commit()
    db.refresh(stop)

    return success_response(StopRead.model_validate(stop))


@router.put("/{stop_id}")
def update_stop(
    stop_id: int,
    stop_in: StopUpdate,
    db: Session = Depends(get_db_session),
) -> dict:
    stop = db.get(Stop, stop_id)
    if stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found.",
        )

    for field, value in stop_in.model_dump(exclude_unset=True).items():
        setattr(stop, field, value)

    db.commit()
    db.refresh(stop)

    return success_response(StopRead.model_validate(stop))


@router.delete("/{stop_id}")
def deactivate_stop(
    stop_id: int,
    db: Session = Depends(get_db_session),
) -> dict:
    stop = db.get(Stop, stop_id)
    if stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found.",
        )

    stop.active = False
    db.commit()
    db.refresh(stop)

    return success_response(StopRead.model_validate(stop))
