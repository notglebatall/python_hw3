from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db_session)):
    service = AuthService(db)
    user = await service.register(email=payload.email, password=payload.password)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db_session)):
    service = AuthService(db)
    token = await service.login(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)
