from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.database.session import get_db_session
from backend.models.vehicle import Vehicle
from backend.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("")
def list_vehicles(db: Session = Depends(get_db_session)) -> dict:
    vehicles = db.scalars(select(Vehicle).order_by(Vehicle.id)).all()
    return success_response(
        [VehicleRead.model_validate(vehicle) for vehicle in vehicles]
    )


@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db_session)) -> dict:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    return success_response(VehicleRead.model_validate(vehicle))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle_in: VehicleCreate,
    db: Session = Depends(get_db_session),
) -> dict:
    vehicle = Vehicle(**vehicle_in.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return success_response(VehicleRead.model_validate(vehicle))


@router.put("/{vehicle_id}")
def update_vehicle(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(get_db_session),
) -> dict:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    for field, value in vehicle_in.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)

    return success_response(VehicleRead.model_validate(vehicle))


@router.delete("/{vehicle_id}")
def deactivate_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db_session),
) -> dict:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    vehicle.active = False
    db.commit()
    db.refresh(vehicle)

    return success_response(VehicleRead.model_validate(vehicle))
