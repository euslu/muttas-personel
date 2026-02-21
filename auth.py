import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt

from db import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class RegisterRequest(BaseModel):
    ad: str
    soyad: str
    email: EmailStr
    password: str
    rol: str = "admin"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_token(user_id: int, email: str, rol: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "rol": rol,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM kullanicilar WHERE email = $1", body.email
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu e-posta adresi zaten kayıtlı.",
            )

        password_hash = hash_password(body.password)
        row = await conn.fetchrow(
            """
            INSERT INTO kullanicilar (ad, soyad, email, password_hash, rol)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, ad, soyad, email, rol
            """,
            body.ad,
            body.soyad,
            body.email,
            password_hash,
            body.rol,
        )

    token = create_token(row["id"], row["email"], row["rol"])
    return {
        "token": token,
        "kullanici": {
            "id": row["id"],
            "ad": row["ad"],
            "soyad": row["soyad"],
            "email": row["email"],
            "rol": row["rol"],
        },
    }


@router.post("/login")
async def login(body: LoginRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, ad, soyad, email, rol, password_hash FROM kullanicilar WHERE email = $1 AND aktif = TRUE",
            body.email,
        )

    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )

    token = create_token(row["id"], row["email"], row["rol"])
    return {
        "token": token,
        "kullanici": {
            "id": row["id"],
            "ad": row["ad"],
            "soyad": row["soyad"],
            "email": row["email"],
            "rol": row["rol"],
        },
    }
