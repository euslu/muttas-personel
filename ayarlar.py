from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db import get_pool
from permissions import decode_token, IK_EDITORS

router = APIRouter(prefix="/ayarlar", tags=["ayarlar"])

AYAR_ROLLER = IK_EDITORS


def require_ayar_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in AYAR_ROLLER:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


class CalismaGunuGuncelle(BaseModel):
    gun_sayisi: int


@router.get("/calisma-gunleri")
async def get_calisma_gunleri(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan, gun_sayisi FROM unvan_calisma_gunu ORDER BY unvan"
        )
        return {r["unvan"]: r["gun_sayisi"] for r in rows}


@router.put("/calisma-gunleri/{unvan}")
async def update_calisma_gunu(
    unvan: str,
    body: CalismaGunuGuncelle,
    token: dict = Depends(require_ayar_editor),
):
    if body.gun_sayisi not in (5, 6):
        raise HTTPException(status_code=400, detail="gun_sayisi 5 veya 6 olmalıdır.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO unvan_calisma_gunu (unvan, gun_sayisi, guncellendi)
            VALUES ($1, $2, NOW())
            ON CONFLICT (unvan) DO UPDATE
              SET gun_sayisi = EXCLUDED.gun_sayisi,
                  guncellendi = NOW()
            """,
            unvan,
            body.gun_sayisi,
        )
    return {"ok": True}
