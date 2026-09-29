from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.database.session import get_db_session
from backend.models.depot import Depot
from backend.schemas.depot import DepotCreate, DepotRead, DepotUpdate

router = APIRouter(prefix="/depots", tags=["depots"])


@router.get("")
def list_depots(db: Session = Depends(get_db_session)) -> dict:
    depots = db.scalars(select(Depot).order_by(Depot.id)).all()
    return success_response([DepotRead.model_validate(depot) for depot in depots])


@router.get("/{depot_id}")
def get_depot(depot_id: int, db: Session = Depends(get_db_session)) -> dict:
    depot = db.get(Depot, depot_id)
    if depot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Depot not found.",
        )

    return success_response(DepotRead.model_validate(depot))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_depot(
    depot_in: DepotCreate,
    db: Session = Depends(get_db_session),
) -> dict:
    depot = Depot(**depot_in.model_dump())
    db.add(depot)
    db.commit()
    db.refresh(depot)

    return success_response(DepotRead.model_validate(depot))


@router.put("/{depot_id}")
def update_depot(
    depot_id: int,
    depot_in: DepotUpdate,
    db: Session = Depends(get_db_session),
) -> dict:
    depot = db.get(Depot, depot_id)
    if depot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Depot not found.",
        )

    for field, value in depot_in.model_dump(exclude_unset=True).items():
        setattr(depot, field, value)

    db.commit()
    db.refresh(depot)

    return success_response(DepotRead.model_validate(depot))


@router.delete("/{depot_id}")
def deactivate_depot(
    depot_id: int,
    db: Session = Depends(get_db_session),
) -> dict:
    depot = db.get(Depot, depot_id)
    if depot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Depot not found.",
        )

    depot.active = False
    db.commit()
    db.refresh(depot)

    return success_response(DepotRead.model_validate(depot))
