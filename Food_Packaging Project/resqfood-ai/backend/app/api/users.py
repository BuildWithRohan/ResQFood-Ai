"""Users API — list, get user details with role info."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.schemas import UserOut, KitchenOut, NGOOut, DriverOut
from app.services.auth_service import get_current_user
from app.models.models import User, Kitchen, NGO, Driver

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [UserOut.model_validate(u) for u in db.query(User).all()]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(u)


@router.get("/kitchens/all", response_model=List[KitchenOut])
def list_kitchens(db: Session = Depends(get_db)):
    return [KitchenOut.model_validate(k) for k in db.query(Kitchen).all()]


@router.get("/ngos/all", response_model=List[NGOOut])
def list_ngos(db: Session = Depends(get_db)):
    return [NGOOut.model_validate(n) for n in db.query(NGO).all()]


@router.get("/drivers/all", response_model=List[DriverOut])
def list_drivers(db: Session = Depends(get_db)):
    return [DriverOut.model_validate(d) for d in db.query(Driver).all()]
