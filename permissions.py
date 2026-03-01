import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

IK_EDITORS    = {"admin", "ik_admin"}
LIMAN_EDITORS = {"admin", "liman_admin"}
GM_EDITORS    = {"admin", "genel_mudur"}
YK_EDITORS    = {"admin", "yk_uyesi"}


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


def require_ik_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in IK_EDITORS:
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
