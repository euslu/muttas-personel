import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import bcrypt
from jose import jwt

from db import get_pool
from permissions import decode_token, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 48

IZIN_VERILEN_ROLLER = {"admin", "ik_admin", "ik_viewer", "liman_admin", "liman_viewer", "genel_mudur", "yk_uyesi", "yk_baskani", "mudur", "koordinasyon_sorumlusu"}

SIFRE_SIFIRLAMA_ROLLER = {"koordinasyon_sorumlusu", "mudur", "genel_mudur"}
DEFAULT_SIFRE = "Muttas2026!"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class RegisterRequest(BaseModel):
    ad: str
    soyad: str
    email: EmailStr
    password: str
    rol: str = "liman_viewer"


class LoginRequest(BaseModel):
    email: str
    password: str


class RolGuncelle(BaseModel):
    rol: str


class SifreDegistir(BaseModel):
    mevcut_sifre: str
    yeni_sifre: str


def create_token(user_id: int, email: str, rol: str, ad: str = "", soyad: str = "", unvan: str = "") -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "rol": rol,
        "ad": ad,
        "soyad": soyad,
        "unvan": unvan,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)



@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, token: dict = Depends(require_admin)):
    if body.rol not in IZIN_VERILEN_ROLLER:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz rol. İzin verilen roller: {sorted(IZIN_VERILEN_ROLLER)}",
        )

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Şifre en az 8 karakter olmalıdır.")

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

    return {
        "kullanici": {
            "id": row["id"],
            "ad": row["ad"],
            "soyad": row["soyad"],
            "email": row["email"],
            "rol": row["rol"],
        },
    }


@router.get("/kullanicilar")
async def list_kullanicilar(token: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, ad, soyad, email, rol, aktif FROM kullanicilar ORDER BY id DESC"
        )
    return [dict(r) for r in rows]


@router.put("/kullanicilar/{uid}/rol")
async def update_rol(uid: int, body: RolGuncelle, token: dict = Depends(require_admin)):
    if body.rol not in IZIN_VERILEN_ROLLER:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz rol. İzin verilen roller: {sorted(IZIN_VERILEN_ROLLER)}",
        )
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM kullanicilar WHERE id = $1", uid)
        if not exists:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

        if body.rol in SIFRE_SIFIRLAMA_ROLLER:
            new_hash = hash_password(DEFAULT_SIFRE)
            await conn.execute(
                "UPDATE kullanicilar SET rol = $2, password_hash = $3, sifre_degistir_gerekli = TRUE WHERE id = $1",
                uid, body.rol, new_hash,
            )
        else:
            await conn.execute("UPDATE kullanicilar SET rol = $2, sifre_degistir_gerekli = FALSE WHERE id = $1", uid, body.rol)

    sifre_sifirlandi = body.rol in SIFRE_SIFIRLAMA_ROLLER
    return {"ok": True, "sifre_sifirlandi": sifre_sifirlandi}


@router.delete("/kullanicilar/{uid}")
async def deactivate_kullanici(uid: int, token: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM kullanicilar WHERE id = $1", uid)
        if not exists:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        if str(uid) == token.get("sub"):
            raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz.")
        await conn.execute("UPDATE kullanicilar SET aktif = FALSE WHERE id = $1", uid)
    return {"ok": True}


@router.post("/login")
async def login(body: LoginRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, ad, soyad, email, rol, password_hash, sifre_degistir_gerekli FROM kullanicilar WHERE email = $1 AND aktif = TRUE",
            body.email,
        )

    if not row or not row["password_hash"] or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )

    async with pool.acquire() as conn:
        p_row = await conn.fetchrow(
            "SELECT unvan FROM personel WHERE tc_kimlik = $1 LIMIT 1",
            body.email,
        )
    unvan = (p_row["unvan"] or "") if p_row else ""

    token = create_token(row["id"], row["email"], row["rol"], row["ad"], row["soyad"], unvan)
    return {
        "token": token,
        "sifre_degistir_gerekli": bool(row["sifre_degistir_gerekli"]),
        "kullanici": {
            "id": row["id"],
            "ad": row["ad"],
            "soyad": row["soyad"],
            "email": row["email"],
            "rol": row["rol"],
            "unvan": unvan,
        },
    }


@router.put("/sifre-degistir")
async def sifre_degistir(body: SifreDegistir, token: dict = Depends(decode_token)):
    if len(body.yeni_sifre) < 8:
        raise HTTPException(status_code=400, detail="Yeni şifre en az 8 karakter olmalıdır.")
    if body.yeni_sifre == body.mevcut_sifre:
        raise HTTPException(status_code=400, detail="Yeni şifre mevcut şifreyle aynı olamaz.")

    user_id = int(token["sub"])
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT password_hash FROM kullanicilar WHERE id = $1 AND aktif = TRUE",
            user_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

        if not verify_password(body.mevcut_sifre, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Mevcut şifreniz hatalı.")

        new_hash = hash_password(body.yeni_sifre)
        await conn.execute(
            "UPDATE kullanicilar SET password_hash = $1, sifre_degistir_gerekli = FALSE WHERE id = $2",
            new_hash, user_id,
        )

    return {"mesaj": "Şifreniz başarıyla değiştirildi."}
