import os
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

IK_EDITORS     = {"admin", "ik_admin", "genel_mudur"}
IZIN_EDITORS   = IK_EDITORS | {"koordinasyon_sorumlusu", "mudur"}
LIMAN_EDITORS  = {"admin", "liman_admin"}
KS_EDITORS     = {"admin", "koordinasyon_sorumlusu", "mudur"}
GM_EDITORS     = {"admin", "genel_mudur"}
YK_EDITORS     = {"admin", "yk_uyesi", "yk_baskani"}

# Cache: devre dışı bırakılan kullanıcılar (5 dakika TTL)
_deaktif_cache: dict[int, float] = {}
_DEAKTIF_TTL = 300  # 5 dakika


async def _kullanici_aktif_mi(user_id: int) -> bool:
    import time
    now = time.time()
    # Cache'de varsa ve süresi dolmamışsa → pasif
    if user_id in _deaktif_cache and now - _deaktif_cache[user_id] < _DEAKTIF_TTL:
        return False
    from db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        aktif = await conn.fetchval("SELECT aktif FROM kullanicilar WHERE id = $1", user_id)
    if aktif is False:
        _deaktif_cache[user_id] = now
        return False
    # Aktif → cache'den kaldır
    _deaktif_cache.pop(user_id, None)
    return True


async def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")
    user_id = payload.get("sub")
    if user_id:
        try:
            uid = int(user_id)
            if not await _kullanici_aktif_mi(uid):
                raise HTTPException(status_code=401, detail="Hesabınız devre dışı bırakılmış.")
        except (ValueError, TypeError):
            pass
    return payload


def require_ik_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in IK_EDITORS:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


def require_izin_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in IZIN_EDITORS:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


def require_liman_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in LIMAN_EDITORS:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


ADMIN_ROLLER = {"admin", "genel_mudur"}


def require_admin(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in ADMIN_ROLLER:
        raise HTTPException(status_code=403, detail="Bu işlem için yönetici yetkisi gereklidir.")
    return token
