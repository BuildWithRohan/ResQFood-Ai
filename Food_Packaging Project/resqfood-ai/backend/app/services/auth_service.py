"""
Authentication service — JWT token management, password hashing, user creation.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_db
from app.models.models import User, Kitchen, NGO, Driver, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: UserRole):
    """Dependency factory that checks the current user has one of the given roles."""
    def checker(user: User = Depends(get_current_user)):
        if user.role not in [r.value if isinstance(r, UserRole) else r for r in roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def register_user(db: Session, data) -> User:
    """Create a user and the associated role-specific record."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        phone=data.phone,
    )
    db.add(user)
    db.flush()

    if data.role == "kitchen":
        kitchen = Kitchen(
            user_id=user.id,
            name=data.kitchen_name or data.full_name,
            address=data.address,
            latitude=data.latitude or 12.9716,
            longitude=data.longitude or 77.5946,
        )
        db.add(kitchen)
    elif data.role == "ngo":
        ngo = NGO(
            user_id=user.id,
            name=data.ngo_name or data.full_name,
            address=data.address,
            latitude=data.latitude or 12.9716,
            longitude=data.longitude or 77.5946,
            capacity=data.capacity or 100,
        )
        db.add(ngo)
    elif data.role == "driver":
        driver = Driver(
            user_id=user.id,
            name=data.driver_name or data.full_name,
            vehicle_type=data.vehicle_type or "bike",
        )
        db.add(driver)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user
