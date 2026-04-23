from fastapi import APIRouter, HTTPException

from api.data.nurses import nurses
from api.schemas.nurse import Nurse

router = APIRouter(prefix="/nurses", tags=["nurses"])


@router.get("/", response_model=list[Nurse])
def list_nurses():
    return nurses


@router.get("/{nurse_id}", response_model=Nurse)
def get_nurse(nurse_id: int):
    for nurse in nurses:
        if nurse.id == nurse_id:
            return nurse
    raise HTTPException(status_code=404, detail="Nurse not found")
