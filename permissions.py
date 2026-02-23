import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

IK_EDITORS    = {"admin", "ik_admin"}
LIMAN_EDITORS = {"admin", "liman_admin"}


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
